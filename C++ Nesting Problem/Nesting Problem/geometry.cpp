//
//  geometry.cpp
//  Nesting Problem
//
//  Created by 爱学习的兔子 on 2020/4/14.
//  Copyright © 2020 Tongji SEM. All rights reserved.
//

#include "data_assistant.cpp"
#include <deque>
#include <iostream>
#include <boost/geometry.hpp>
#include <boost/geometry/geometries/point_xy.hpp>
#include <boost/geometry/geometries/polygon.hpp>
#include <boost/foreach.hpp>
#include <boost/geometry/algorithms/for_each.hpp>

using namespace boost::geometry;
using namespace std;

#define BIAS 0.000001

// 基础定义
typedef model::d2::point_xy<double> Point;
typedef model::polygon<Point> Polygon;
typedef model::linestring<Point> LineString;


// 封装获得全部点的函数
template <typename Point>
class AllPoint{
private :
    VectorPoints *temp_all_points;
public :
    AllPoint(VectorPoints *all_points){
        temp_all_points=all_points;
    };
    inline void operator()(Point& pt)
    {
        vector<double> new_pt={get<0>(pt),get<1>(pt)};
        (*temp_all_points).push_back(new_pt);
    }
};

//主要包含注册多边形、转化多边形
class GeometryProcess{
public:
    /*
     数组转化为多边形
     */
    static void convertPoly(vector<vector<double>> poly, Polygon &Poly){
        // 空集的情况
        if(poly.size()==0){
            read_wkt("POLYGON(())", Poly);
            return;
        }
        // 首先全部转化为wkt格式
        string wkt_poly="POLYGON((";
        for (int i = 0; i < poly.size();i++){
            wkt_poly+=to_string(poly[i][0]) + " " + to_string(poly[i][1]) + ",";
            if(i==poly.size()-1){
                wkt_poly+=to_string(poly[0][0]) + " " + to_string(poly[0][1]) + "))";
            }
        };
        // 然后读取到Poly中
        read_wkt(wkt_poly, Poly);
    };
    /*
     通过for each point遍历
     */
    static void getAllPoints(list<Polygon> all_polys,VectorPoints &all_points){
        for(auto poly_item:all_polys){
            VectorPoints temp_points;
            getGemotryPoints(poly_item,temp_points);
            all_points.insert(all_points.end(),temp_points.begin(),temp_points.end());
        }
    };
    // 获得vector<list<VectorPoints>>的多边形（并非全部点）
    static void getListPolys(vector<list<Polygon>> list_polys,vector<VectorPoints> &all_polys){
        for(auto _list:list_polys){
            for(Polygon poly_item:_list){
                VectorPoints poly_points;
                getGemotryPoints(poly_item,poly_points);
                all_polys.push_back(poly_points);
            }
        }
    };
    // 获得某个集合对象的全部点
    static void getGemotryPoints(Polygon poly,VectorPoints &temp_points){
        for_each_point(poly, AllPoint<Point>(&temp_points));
    };
};

// 包含处理函数
class PackingAssistant{
public:
    /*
     获得Inner Fit Rectangle
     */
    static void getIFR(VectorPoints polygon,double container_width,double container_length,VectorPoints &IFR){
        // 初始参数，获得多边形特征
        VectorPoints border_points;
        getBorder(polygon,border_points);
                
        double poly_width_left=border_points[3][0]-border_points[0][0];
        double poly_width_right=border_points[2][0]-border_points[3][0];
        double poly_height=border_points[3][1]-border_points[1][1];

        // IFR具体计算（从左上角顺时针计算）
        IFR.push_back({poly_width_left,container_width});
        IFR.push_back({container_length-poly_width_right,container_width});
        IFR.push_back({container_length-poly_width_right,poly_height});
        IFR.push_back({poly_width_left,poly_height});
    };
    /*
     移动某个多边形
     */
    static void slidePoly(VectorPoints &polygon,double delta_x,double delta_y){
        for(int i=0;i<polygon.size();i++){
            polygon[i][0]=polygon[i][0]+delta_x;
            polygon[i][1]=polygon[i][1]+delta_y;
        }
    };
    /*
     移动多边形到某个位置（参考点）
     */
    static void slideToPosition(VectorPoints &polygon,vector<double> target_pt){
        vector<double> refer_pt;
        getReferPt(polygon,refer_pt);
        cout<<"多边形";
        PrintAssistant::print2DVector(polygon,true);
        cout<<"参考点:"<<refer_pt[0]<<","<<refer_pt[1]<<endl;
        cout<<"目标点:"<<target_pt[0]<<","<<target_pt[1]<<endl;
        double delta_x=target_pt[0]-refer_pt[0];
        double delta_y=target_pt[1]-refer_pt[1];
        for(int i=0;i<polygon.size();i++){
            polygon[i][0]=polygon[i][0]+delta_x;
            polygon[i][1]=polygon[i][1]+delta_y;
        }
    };
    /*
     获得多边形的所有的边界情况min_x min_y max_x max_y
     */
    static void getBound(VectorPoints polygon,vector<double> &bound){
        VectorPoints border_points;
        getBorder(polygon,border_points);
        bound={border_points[0][0],border_points[1][1],border_points[2][0],border_points[3][1]};
    };
    /*
     遍历获得一个多边形的最左侧点
     */
    static void getBottomLeft(VectorPoints polygon,vector<double> &bl_point){
        bl_point={999999999,999999999};
        for(auto point:polygon){
            if(point[0]<bl_point[0] || (point[0]==bl_point[0]&&point[1]<bl_point[1]) ){
                bl_point[0]=point[0];
                bl_point[1]=point[1];
            }
        };
    };
    /*
     仅仅获得最右侧点，同样为逆时针处理（用于判断是逗超出界限）
     */
    static void getRightPt(VectorPoints polygon,vector<double> &right_pt){
        right_pt={-9999999999,0};
        int poly_size=(int)polygon.size();
        for(int i=poly_size-1;i>=0;i--){
            if(polygon[i][0]>right_pt[0]){
                right_pt[0]=polygon[i][0];
                right_pt[1]=polygon[i][1];
            }
        }
    };
    /*
     仅仅获得参考点，是第一个Top位置，需要逆时针处理（NFP为逆时针）
     */
    static void getReferPt(VectorPoints polygon,vector<double> &refer_pt){
        refer_pt={0,-9999999999};
        int poly_size=(int)polygon.size();
        for(int i=poly_size-1;i>=0;i--){
            if(polygon[i][1]>refer_pt[1]){
                refer_pt[0]=polygon[i][0];
                refer_pt[1]=polygon[i][1];
            }
        }
    };
    /*
     仅仅获得底部位置（用于NFP计算），是第一个Bottom位置，需要逆时针处理
     */
    static void getBottomPt(VectorPoints polygon,vector<double> &bottom_pt){
        bottom_pt={0,9999999999};
        int poly_size=(int)polygon.size();
        for(int i=poly_size-1;i>=0;i--){
            if(polygon[i][1]<bottom_pt[1]){
                bottom_pt[0]=polygon[i][0];
                bottom_pt[1]=polygon[i][1];
            }
        }
    };
    
    /*
     获得多边形的边界四个点，border_points有left bottom right top四个点
     暂时不考虑参考点，参考点统一逆时针旋转第一个最上方的点
     */
    static void getBorder(VectorPoints polygon,VectorPoints &border_points){
        // 增加边界的几个点
        border_points.push_back(vector<double>{9999999999,0});
        border_points.push_back(vector<double>{0,999999999});
        border_points.push_back(vector<double>{-999999999,0});
        border_points.push_back(vector<double>{0,-999999999});
        // 遍历所有的点，分别判断是否超出界限
        int poly_size=(int)polygon.size();
        for(int i=poly_size-1;i>=0;i--){
            // 左侧点判断
            if(polygon[i][0]<border_points[0][0]){
                border_points[0][0]=polygon[i][0];
                border_points[0][1]=polygon[i][1];
            }
            // 下侧点判断
            if(polygon[i][1]<border_points[1][1]){
                border_points[1][0]=polygon[i][0];
                border_points[1][1]=polygon[i][1];
            }
            // 右侧点判断
            if(polygon[i][0]>border_points[2][0]){
                border_points[2][0]=polygon[i][0];
                border_points[2][1]=polygon[i][1];
            }
            // 上侧点判断
            if(polygon[i][1]>border_points[3][1]){
                border_points[3][0]=polygon[i][0];
                border_points[3][1]=polygon[i][1];
            }
        };
    };
    
    // 判断两个多边形是否重叠
    static bool judgeOverlap(VectorPoints poly1,VectorPoints poly2){
        Polygon Poly1,Poly2;
        GeometryProcess::convertPoly(poly1,Poly1);
        GeometryProcess::convertPoly(poly2,Poly2);
        return intersects(Poly1, Poly2);
    };
    
    // 获得两个多边形的重叠情况
    static double overlapArea(VectorPoints poly1,VectorPoints poly2){
        double overlap_area=0;
        
        Polygon Poly1,Poly2;
        GeometryProcess::convertPoly(poly1,Poly1);
        GeometryProcess::convertPoly(poly2,Poly2);
        
        // 获得重叠情况
        deque<Polygon> output;
        intersection(Poly1, Poly2, output);
        
        // 遍历计算重叠面积
        BOOST_FOREACH(Polygon const& p, output)
        {
            overlap_area+=area(p);
        }
        if(overlap_area>BIAS){
            return overlap_area;
        }else{
            return 0;
        }
    };
    // 获得List对象的全部重叠
    static double totalArea(list<Polygon> poly_list){
        double total_area=0;
        BOOST_FOREACH(Polygon const& p, poly_list)
        {
            total_area+=area(p);
        }
        return total_area;
    };
    // 获得当前排样的宽度
    static double arrangetLenth(vector<VectorPoints> all_polys){
        double length=0;
        for(VectorPoints poly:all_polys){
            vector<double> pt;
            getRightPt(poly,pt);
            if(pt[0]>length){
                length=pt[0];
            }
        }
        return length;
    }
};

// 获得NFP
class NFPAssistant{
protected:
    csv::Reader nfp_result;
    int poly_num;
    int orientation_num;
    vector<VectorPoints> NPFs; // 存储全部的NFP，按行存储
public:
    /*
     预加载全部的NFP，直接转化到NFP中
     */
    NFPAssistant(string _path,int poly_num,int orientation_num){
        nfp_result.read(_path);
        this->poly_num=poly_num;
        this->orientation_num=orientation_num;
        cout<<"加载全部NFP"<<endl;
        while(nfp_result.busy()) {
            if (nfp_result.ready()) {
                auto row = nfp_result.next_row();
                VectorPoints nfp;
                if(row["nfp"]!=""){
                    DataAssistant::load2DVector(row["nfp"],nfp);
                    NPFs.push_back(nfp);
                }
            }
        }
    };
    /*
     读取NFP的确定行数，i为固定形状，j为非固定形状,oi/oj为形状
     */
    void getNFP(int i,int j, int oi, int oj, VectorPoints poly_j ,VectorPoints &nfp){
        // 获得原始的NFP
        int row_num= i*192+j*16+oi*4+oj;
        nfp=NPFs[row_num];
        // 将NFP移到目标位置
        vector<double> bottom_pt;
        PackingAssistant::getBottomPt(poly_j,bottom_pt);
        PackingAssistant::slidePoly(nfp,bottom_pt[0],bottom_pt[1]);
    }
};

// 处理多个多边形的关系
class PolygonsOperator{
public:
    // 计算多边形的差集合
    static void polysDifference(list<Polygon> &feasible_region, Polygon sub_region){
        // 逐一遍历求解重叠
        list<Polygon> new_feasible_region;
        for(auto region_item:feasible_region){
            list<Polygon> output;
            difference(region_item, sub_region, output);
            DataAssistant::appendList(new_feasible_region,output);
        };
        // 将新的Output全部输入进去
        feasible_region.clear();
        copy(new_feasible_region.begin(), new_feasible_region.end(), back_inserter(feasible_region));
    }
    // 逐一遍历求差集
    static void polyListDifference(list<Polygon> &feasible_region, list<Polygon> sub_region){
        for(auto region_item:sub_region){
            polysDifference(feasible_region,region_item);
        }
    }
    // List和一个Poly的差集
    static void listToPolyIntersection(list<Polygon> region_list, Polygon region, list<Polygon> &inter_region){
        for(auto region_item:region_list){
            list<Polygon> output;
            intersection(region_item, region, output);
            DataAssistant::appendList(inter_region,output);
        }
    }
    // List和List之间的交集
    static void listToListIntersection(list<Polygon> region1, list<Polygon> region2, list<Polygon> &inter_region){
        for(auto region_item1:region1){
            for(auto region_item2:region2){
                list<Polygon> output;
                intersection(region_item1, region_item2, output);
                DataAssistant::appendList(inter_region,output);
            }
        }
    }
    // 判断某个List是否为空
    static bool judgeListEmpty(list<Polygon> poly_list){
        for(auto item:poly_list){
            if(area(item)>BIAS){
                return false;
            }
        }
        return true;
    }
    // 计算多边形的交集
    void polysUnion(){
        // 测试基础
        Polygon green, blue;

        vector<Polygon> output;
        union_(green, blue, output);

        int i = 0;
        cout << "green || blue:" << endl;
        BOOST_FOREACH(Polygon const& p, output)
        {
            cout << i++ << ": " << area(p) << endl;
        }
    }
    /*
     List数组的增长
     */
    static void appendPolyList(list<Polygon> &old_list,list<Polygon> &new_list){
        for(auto item:new_list){
            if(area(item)>BIAS){
                Polygon new_item;
                PolygonsOperator::convertToFeasible(new_item,item);
                old_list.push_back(new_item);
            }
        }
    }
    /*
     将不可行转化为可行
     */
    static void convertToFeasible(Polygon new_item,Polygon item){
        // 确认所有的点
        VectorPoints all_points;
        VectorPoints new_all_points;
        GeometryProcess::getGemotryPoints(item,all_points);
        // 判断点是否重叠了
        for(int i = 0; i < all_points.size(); i++){
            VectorPoints line1, line2;
            line1 = {all_points[i], all_points[i+1]};
            if(i == all_points.size() - 1){
                line2 = {all_points[0], all_points[1]};
            }else if (i == all_points.size() - 2){
                line2 = {all_points[i+1], all_points[0]};
            }else{
                line2 = {all_points[i+1], all_points[i+2]};
            }
            // 首先判断垂直情况
            double delta_x1, delta_y1, delta_x2, delta_y2;
            delta_x1 = line1[1][0] - line1[0][0];
            delta_y1 = line1[1][1] - line1[0][1];
            delta_x2 = line2[1][0] - line2[0][0];
            delta_y2 = line2[1][1] - line2[0][1];
            if(delta_x1 < BIAS && delta_x2 < BIAS){
                continue;
            }else if(delta_x1 < BIAS || delta_x2 < BIAS){
                new_all_points.push_back(all_points[i+1]);
            }else{
                // 判断非垂直情况
                double k1 = delta_y1/delta_x1;
                double k2 = delta_y2/delta_x2;
                if(abs(abs(k1) - abs(k2)) < BIAS){
                    continue;
                }
            }
        }
    }
};
