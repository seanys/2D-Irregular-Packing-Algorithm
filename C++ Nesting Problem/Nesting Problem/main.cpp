//
//  main.cpp
//  Nesting Problem
//
//  Created by Yang Shan on 2020/4/13.
//  Copyright © 2020 Tongji SEM. All rights reserved.
//

#include <iostream>
#include <vector>
#include <stdbool.h>
#include <csv/reader.hpp>
#include "plot.cpp"
#include "geometry.cpp"
#include <time.h>
#include <algorithm>



class LPSearch{
protected:
    VectorPoints cur_ifr; // 获得当前的IFR
    double poly_num; // 形状总数
    vector<VectorPoints> all_nfps; // 获得当前全部NFP
    vector<Polygon> all_nfps_poly; // 获得当前全部NFP的Polygon模型
    vector<vector<vector<double>>> edges_target_funs,points_target_funs; // 分别获得直线和点的目标函数
    
    PolysArrange cur_solution; // 记录当前解，加载读取时使用
    
    vector<VectorPoints> best_polys,polys; // 暂存当前的全部形状
    vector<int> best_orientation,cur_orientation; // 当前最佳情况和当前情况采用的方向
    double best_length,cur_length; // 当前宽度和最佳宽度

    vector<int> polys_type; // 所有形状情况（不变）
    double width; // 放置宽度（不变）

    vector<vector <double>> poly_overlap; // 重叠情况
    vector<vector <double>> nfp_overlap_pair; // NFP的重叠情况
    vector<vector <double>> nfp_overlap_list; // 每个NFP的重叠对象（计算相交）
    vector<vector <double>> miu; // 重叠情况
    
    vector<vector <VectorPoints>> all_polygons; // 全部形状的加载
    
    int choosed_index; // 当前选择的index
    
    NFPAssistant *nfp_assistant; // NFP辅助操作
    
    vector<list<Polygon>> nfp_sub_ifr; // 除去IFR后的NFP，全部存为Vector<VectorPoints>（计算相交情况）
    vector<vector<list<Polygon>>> nfp_sub_ifr_phase; // 各个阶段的NFP的记录
    vector<vector<vector<int>>> target_indexs; // 获得各个阶段交集的目标区域
public:
    LPSearch(){
        DataAssistant::readAllPolygon(all_polygons); // 加载各个方向的形状
        DataAssistant::readBLF(3,cur_solution); // 读取BLF的解
        nfp_assistant = new NFPAssistant("/Users/sean/Documents/Projects/Data/fu_clock.csv",cur_solution.type_num,4); // NFP辅助
        
        polys = cur_solution.polys; // 当前的形状，记录形状变化
        cur_orientation = cur_solution.polys_orientation; // 赋值全部形状（变化）
        cur_length = PackingAssistant::arrangetLenth(polys); // 当前长度（变化）
        
        best_polys = cur_solution.polys; // 最佳结果存储
        best_length = cur_length; // 最佳长度（变化）
        best_orientation = cur_solution.polys_orientation; // 最佳长度（变化）

        width = cur_solution.width; // 宽度（不变）
        poly_num = cur_solution.total_num; // 形状总数（不变）
        polys_type = cur_solution.polys_type; // 形状类别（不变）
        
    };
    void run(){
        // 限制检索时间是否超过时间
        double ration_dec=0.04,ration_inc=0.01;
//        double max_time=1200;
        
        shrinkBorder(ration_dec);
        
        // 执行最小化重叠后，判断解是否可行
        minimizeOverlap();
        
    };
    // 计算收缩后的情况
    void shrinkBorder(double ration_dec){
        cur_length = best_length*(1 - ration_dec);
        for(int i=0;i<poly_num;i++){
            vector<double> right_pt;
            PackingAssistant::getRightPt(polys[i],right_pt);
            if(right_pt[0]>cur_length){
                PackingAssistant::slidePoly(polys[i], cur_length-right_pt[0], 0);
            }
        }
    };
    // 扩大边界
    void extendBorder(double ration_inc){
        cur_length = best_length*(1 - ration_inc);
    };
    
    
    // 输入序列形状，每次处理一个序列
    void minimizeOverlap(){
        initial2DVector(1,poly_num,miu); // 初始化Miu的值
        int it=0,N=1; // 循环次数限制
        double lowest_overlap=999999999; // 重叠的处理
        
        while(it < N){
            // 生成一个序列，逐一赋值并寻找更优位置
            vector<int> search_permutation;
            randomPermutation(search_permutation);
            
            for(auto index:search_permutation){
                for(auto oi:{0,1,2,3}){
                    lpSearch(index,oi);
                }
            }
            
            // 获得本序列结束后的情况
            double cur_overlap = getTotalPD();
            if(cur_overlap<BIAS){
                cout<<"本次计算结束，没有重叠"<<endl;
                break;
            }else if (cur_overlap < lowest_overlap){
                lowest_overlap = cur_overlap;
                it=0;
            }
            // 更新Miu和循环次数，开始下一次检索
            cout<<"当前重叠:"<<cur_overlap<<endl;
            updateMiu();
            it++;
        };
        if(N == it){
            cout<<"超出检索次数"<<endl;
        }
        
    };
    
    void lpSearch(int i,int oi){
        
    }

    void searchOnePoly(){
        // 初始化形状间重叠，并判断当前选择形状是否有重叠
        
        if(judgePositionOverlap()==false){
            cout<<"该形状不存在重叠"<<endl;
            return;
        }
        // 获得初始位置，后续求解最优位置，需要比较
        vector<double> original_position;
        PackingAssistant::getReferPt(polys[choosed_index], original_position);
        
        // 获得全部NFP和IFR，外加所有多边形的目标函数
        getNFPIFR(choosed_index,cur_orientation[choosed_index]);
                
        // 存储最佳的位置/深度/方向
        double best_depth=getInitialDepth(original_position);
        int best_orientation=cur_orientation[choosed_index];
        vector<double> best_position=original_position;
                
        // 测试每个角度检索位置，获得NFP、IFR，再寻找最佳的位置
        for(int orientation=0;orientation<4;orientation++){
            // 获得对应的NFP和IFR
            getNFPIFR(choosed_index,orientation);
            PrintAssistant::print2DVector(cur_ifr,true);
            
            // 判断IFR除去NFP之后是否还有空隙，若有，则更新并返回
            list<Polygon> ifr_sub_nfp;
            getIfrSubNfp(ifr_sub_nfp);
            if(PackingAssistant::totalArea(ifr_sub_nfp)>BIAS){
                cout<<"IFRSubNFP存在可能区域，直接调用"<<endl;
                best_depth=0; // 最低深度为0
                best_orientation=orientation; // 最佳方向
                getFirstPoint(best_position,ifr_sub_nfp); // 最佳位置
                break;
            }else{
                cout<<"不存在可行区域，寻找最低深度位置"<<endl;
            }
            
            
            vector<double> new_poistion;
            double new_depth=searchForBestPosition(new_poistion);
            
            // 比较新的结果是否需要更新最值，需要更新则更新深度、最佳位置和最佳方向
            if(new_depth<best_depth){
                cout<<"检索到更低高度的位置"<<endl;
                best_depth=new_depth;
                best_position=new_poistion;
                best_orientation=orientation;
            }else{
                cout<<"没有检索到更低位置"<<endl;
            }
        }
        
        // 如果最佳的位置和原始位置不一样，则移动当前解，并更新重叠
        if(best_position[0]!=original_position[0]||best_position[1]!=original_position[1]){
            cout<<"平移多边形"<<endl;
            PltFunc::polysShow(polys);
            
            polys[choosed_index]=all_polygons[choosed_index][best_orientation]; // 更新选择形状
            PackingAssistant::slideToPosition(polys[choosed_index], best_position); // 移到最佳位置
            updatePD(choosed_index); // 更新全部重叠
            
            PltFunc::polysShow(polys);
        }

    };
    
    // 判断某个形状当前位置是否有重叠（4.26测试）
    bool judgePositionOverlap(){
        for(auto item:poly_overlap[choosed_index]){
            if(item>0){
                return true;
            }
        }
        return false;
    };
    
    // 获得某个形状的全部NFP和IFR（4.26测试）
    void getNFPIFR(int j,int oj){
        // 获得全部的NFP
        all_nfps={};
        all_nfps_poly={};
        for(int i=0;i<poly_num;i++){
            // 如果等于则直接加空的
            if(i==j){
                all_nfps.push_back({});
                continue;
            }
            // 获得对应的NFP
            VectorPoints nfp;
            nfp_assistant->getNFP(polys_type[i], polys_type[j], cur_orientation[i], oj, polys[i], nfp);
            all_nfps.push_back(nfp);
            // 获得对应NFP的Polygon模型
            Polygon nfp_poly;
            GeometryProcess::convertPoly(nfp, nfp_poly);
            all_nfps_poly.push_back(nfp_poly);
        }
        // 获得IFR形状
        cur_ifr={};
        PackingAssistant::getIFR(all_polygons[j][oj], width, cur_length, cur_ifr);
    };
    
    // 获得最小的Penetration Depth的位置
    double searchForBestPosition(vector<double> &position){
        double min_depth=9999999999;
        
        vector<double> coeff;
        edge = {}
        getEdgeCoeff(coeff,edge);
        
        return min_depth;
    };
    
    // 获得某个位置与某个形状的最低高度（返回的结果调整过）
    double getPointPolyDepth(vector<vector<double>> poly,vector<double> pt){
        double min_depth=9999999;
        // 遍历全部的边对象 abs(ax+by+c)
        for(auto edge_target:edges_target_funs[poly_index]){
            double value=abs(edge_target[0]*pt[0]+edge_target[1]*pt[1]+edge_target[2]);
            if(value<min_depth){
                min_depth=value;
            }
        }
        return min_depth*miu[choosed_index][poly_index];
    };
    
    // 获得某个位置的最低Depth（与全部相关多边形）
    double getPointDepth(vector<double> pt,vector<int> all_nfp_indexs){
        double depth=0;
        for(auto nfp_index:all_nfp_indexs){
            depth+=getPointPolyDepth(, pt);
        }
        return depth;
    };
    
    // 在初始化之后获得该形状的初始深度（最初计算出的高度）
    double getInitialDepth(vector<double> pt){
        double poly_depth=0;
        for(int i=0;i<poly_num;i++){
            // 如果没有重叠直接跳过（重叠情况每次变更都会更新）
            if(poly_overlap[choosed_index][i]==0||i==choosed_index){
                continue;
            }
            poly_depth+=getPointPolyDepth(i,pt);
        }
        return poly_depth;
    };
    
    // 判断IFR除去全部NFP后还有剩余（4.26检测）
    void getIfrSubNfp(list<Polygon> &feasible_region){
        // 计算IFR以及可行区域
        Polygon IFR;
        GeometryProcess::convertPoly(cur_ifr, IFR);
        feasible_region={IFR};
        // 逐步遍历全部NFP求差集
        for(int i=0; i < poly_num; i++){
            if(i == choosed_index){
                continue;
            }
            auto nfp=all_nfps[i];
            Polygon nfp_poly;
            GeometryProcess::convertPoly(nfp, nfp_poly);
            PolygonsOperator::polysDifference(feasible_region, nfp_poly);
        }
    };
    
    // 获得一阶NFP除去IFR的情况（4.26测试）
    void getNfpInterIfr(){
        // 辅助计算最终情况的函数（需要先归零）
        nfp_sub_ifr_phase={};
        target_indexs={};
        nfp_sub_ifr_phase.push_back({});
        target_indexs.push_back({});
        // 首先获得IFR的情况
        Polygon ifr_poly;
        GeometryProcess::convertPoly(cur_ifr, ifr_poly);
        // 获得除去IFR的后的
        for(int i=0;i<poly_num;i++){
            // 先求NFP
            Polygon nfp_poly;
            auto nfp=all_nfps[i];
            GeometryProcess::convertPoly(nfp, nfp_poly);
            // 再求划分之后的结果
            list<Polygon> nfp_poly_list={nfp_poly};
            list<Polygon> inter_region;
            PolygonsOperator::listToPolyIntersection(nfp_poly_list, ifr_poly, inter_region);
            nfp_sub_ifr.push_back(inter_region);
            // 阶段性计算存储
            nfp_sub_ifr_phase[0].push_back(inter_region);
            target_indexs[0].push_back({});
            target_indexs[0][target_indexs[0].size()-1].push_back(i);
        }
    };
    
    static void showVectorPolyList(vector<list<Polygon>> poly_list){
        vector<VectorPoints> all_polys_to_show;
        GeometryProcess::getListPolys(poly_list,all_polys_to_show);
        PrintAssistant::print3DVector(all_polys_to_show, true);
        PltFunc::polysShow(all_polys_to_show);
    };
    
    // 获得NFP的重叠情况（4.26测试）
    void getNFPOverlap(){
        // 初始化两个数组
        initial2DVector(0, poly_num, nfp_overlap_pair);
        initial1DVector(poly_num,nfp_overlap_list);
        // 逐步判断和求解
        for(int i=0;i<poly_num-1;i++){
            nfp_overlap_pair.push_back({});
            for(int j=i+1;j<poly_num;j++){
                if(PackingAssistant::judgeOverlap(all_nfps[i],all_nfps[j])==true){
                    nfp_overlap_list[i].push_back(j);
                    nfp_overlap_pair[i][j] = 1;
                    nfp_overlap_pair[j][i] = 1;
                }
            }
        }
    };
    
    // 初始化当前的整个重叠（两两间的重叠）（4.26测试）
    void initialPD(){
        initial2DVector(0,poly_num,poly_overlap);
        for(int i=0;i<poly_num-1;i++){
            for(int j=i+1;j<poly_num;j++){
                double overlap=PackingAssistant::overlapArea(polys[i], polys[j]);
                poly_overlap[i][j]=overlap;
                poly_overlap[j][i]=overlap;
            }
        }
    };
    
    // 更新多边形的重叠情况（单独更新某个形状）（4.26测试）
    void updatePD(int i){
        for(int j=0;j<poly_num;j++){
            if(i==j){
                continue;
            }
            double overlap=PackingAssistant::overlapArea(polys[i], polys[j]);
            poly_overlap[j][i]=overlap;
            poly_overlap[i][j]=overlap;
        }
    };
        
    /*
     以下函数可以封装到PackingAssistant中！
     */
    
    // 获得某个多边形所有的边（4.26测试）
    void getAllEdges(VectorPoints poly,vector<VectorPoints> &all_edges){
        for(int i=0;i<poly.size();i++){
            VectorPoints edge;
            if(i==poly.size()-1){
                edge={poly[i],poly[0]};
            }else{
                edge={poly[i],poly[i+1]};
            }
            all_edges.push_back(edge);
        }
    };
    
    // 获得点到直线的距离的系数参数（4.26测试）
    void getEdgeCoeff(vector<double> &coeff, VectorPoints edge){
        double A=edge[0][1]-edge[1][1];
        double B=edge[1][0]-edge[0][0];
        double C=edge[0][0]*edge[1][1]-edge[1][0]*edge[0][1];
        double D=sqrt(A*A+B*B);
        coeff={A/D,B/D,C/D};
    };
    
    // 初始化二维数组（4.26测试）
    void initial2DVector(double initial_value,double initial_size,vector<vector<double>> &target){
        target={};
        for(int i=0;i<initial_size;i++){
            target.push_back({});
            for(int j=0;j<initial_size;j++){
                target[i].push_back(initial_value);
            }
        }
    };
    
    // 初始化一维数组（4.26测试）
    void initial1DVector(double initial_size,vector<vector<double>> &target){
        target={};
        for(int i=0;i<initial_size;i++){
            target.push_back({});
        }
    };
    
    // 获得随机序列
    void randomPermutation(vector<int> &permutation){
        cout<<"随机化序列"<<endl;
        srand((unsigned)time(NULL));
        for(int i=0;i<poly_num;i++){
            permutation.push_back(i);
        }
        random_shuffle(permutation.begin(),permutation.end());
    };
    
    // 更新权重参数Miu
    void updateMiu(){
        // 寻找最大的重叠
        double _max=0;
        for(auto line:poly_overlap){
            for(auto item:line){
                if(item>_max){
                    _max=item;
                }
            }
        }
        // 更新全部的Miu
        for(int i=0;i<poly_num;i++){
            for(int j=0;j<poly_num;j++){
                miu[i][j]+=poly_overlap[i][j]/_max;
                miu[j][i]+=poly_overlap[j][i]/_max;
            }
        }
    };

    // IFR Sub NFP后选择第一个点
    void getFirstPoint(vector<double> &first_point,list<Polygon> poly_list){
        VectorPoints all_points;
        GeometryProcess::getAllPoints(poly_list, all_points);
        first_point=all_points[0];
    };
};

int main(int argc, const char * argv[]) {
    LPSearch *lp;
    lp=new LPSearch();
    lp->run();
    
//    VectorPoints poly1,poly2;
//    PackingAssistant::overlapArea(poly1,poly2);

//    WriterAssistant::writeCSV();
    
    
    return 0;
}

