//
//  Data Assistant.cpp
//  Nesting Problem
//
//  Created by Sean Yang on 2020/4/14.
//  Copyright © 2020 Tongji SEM. All rights reserved.
//
//  CSV Kits
//  https://github.com/p-ranav/csv
//
//  包含内容：基础定义、输出辅助、形状加载、NFP加载和获取、CSV写

#include "data_assistant.hpp"
#include <algorithm>
#include <algorithm>
#include <csv/reader.hpp>
#include <csv/writer.hpp>
#include <x2struct/x2struct.hpp>

using namespace x2struct;

class DataAssistant{
public:
    void test(){
        PolysArrange blf_result;
        readBLF(1,blf_result);
    };
    /*
     直接读取指定的Index
     */
    static void readCSV(){
        csv::Reader foo;
        foo.read("/Users/sean/Documents/Projects/Packing-Algorithm/record/c_blf.csv");
        auto rows = foo.rows();
        cout<<rows[1]["orientation"]<<endl;
    };
    /*
     获得对应数据库的所有形状，是一个顺序
     */
    static void readData(PolysArrange &polys_arrange){
        // 初步读取
        csv::Reader foo;
        foo.read("/Users/sean/Documents/Projects/Packing-Algorithm/data/fu.csv");
        // 基础定义
        polys_arrange.width=760;
        polys_arrange.total_area=433200;
        int row_index=0;
        while(foo.busy()) {
            if (foo.ready()) {
                // 下一行（默认跳过第一行）
                auto row = foo.next_row();
                // 加载全部形状
                int poly_num=stoi(row["num"]);
                for(int i=0;i<poly_num;i++){
                    // 加载形状（暂时每个都加载）
                    vector<vector<double>> new_poly;
                    load2DVector(row["clock_polygon"],new_poly);
                    normData(&new_poly, 20);
                    // 修改对应性质
                    polys_arrange.polys.push_back(new_poly);
                    polys_arrange.polys_type.push_back(row_index);
                    polys_arrange.polys_orientation.push_back(0);
                    polys_arrange.polys_position.push_back(vector<double> {0,0});
                }
                // 统计数目
                polys_arrange.total_num+=poly_num;
                polys_arrange.type_num++;
                row_index++;
            }
        }
    };
    /*
     加载某个形状的全部方向
     */
    static void readAllPolygon(vector<vector <VectorPoints>> &all_polygons){
        // 初步读取
        csv::Reader foo;
        foo.read("/Users/sean/Documents/Projects/Data/fu_orientation.csv");
        // 加载全部形状
        int row_index=0;
        while(foo.busy()) {
            if (foo.ready()) {
                // 下一行（默认跳过第一行）
                auto row = foo.next_row();
                // 设置本轮读取
                vector <string> all_lines={"clock_o_0","clock_o_1","clock_o_2","clock_o_3"};
                all_polygons.push_back({});
                // 加载每个角度对应的形状
                for(auto line:all_lines){
                    vector<vector<double>> new_poly;
                    load2DVector(row[line],new_poly);
                    all_polygons[row_index].push_back(new_poly);
                }
                row_index++;
            }
        }
    };
    /*
     读取BLF某一行的结果，包括宽度、方向、总面积、位置和形状
     */
    static void readBLF(int index,PolysArrange &blf_result){
        csv::Reader foo;
        foo.read("/Users/sean/Documents/Projects/Packing-Algorithm/record/c_blf.csv");
        auto rows = foo.rows();
        // 加载宽度和总面积
        blf_result.width=stod(rows[index]["width"]);;
        blf_result.total_area=stod(rows[index]["total_area"]);
        // 所有方向/位置/形状
        load1DVector(rows[index]["polys_orientation"],blf_result.polys_orientation);
        load3DVector(rows[index]["polys"],blf_result.polys);
        // 设置形状总数和类型总数——后续存储好
        blf_result.total_num=(int)blf_result.polys_orientation.size();
        blf_result.type_num=(int)blf_result.polys_orientation.size();
        // 暂时采用全部不一致的情况，后续增加该列即可
        for(int i=0;i<blf_result.polys_orientation.size();i++){
            blf_result.polys_type.push_back(i);
        }
    };
    
    /*
     Push新的Vector
     */
    static void pushVector(VectorPoints poly,VectorPoints new_poly){
        for(auto pt:new_poly){
            poly.push_back(vector<double> {pt[0],pt[1]});
        }
        PrintAssistant::print2DVector(poly,false);
    };
    
    /*
     标准化数据（扩大或者缩小倍数）
     */
    static void normData(VectorPoints *poly,double multiplier){
        for(int i=0; i<(*poly).size();i++){
            (*poly)[i][0]=(*poly)[i][0]*multiplier;
            (*poly)[i][1]=(*poly)[i][1]*multiplier;
        }
    };
    
    /*
     加载一维的数组向量并返回
     */
    template <typename T>
    static void load1DVector(string str,vector<T> &vec){
        str.erase(remove(str.begin(), str.end(), '\"'), str.end());
        X::loadjson(str, vec, false);
    };
    
    /*
     加载二维数组
     */
    template <typename T>
    static void load2DVector(string str,vector<vector<T>> &vec){
        str.erase(remove(str.begin(), str.end(), '\"'), str.end());
        X::loadjson(str, vec, false);
    };
    
    /*
     加载三维数组
     */
    template <typename T>
    static void load3DVector(string str,vector<vector<vector<T>>> &vec){
        str.erase(remove(str.begin(), str.end(), '\"'), str.end());
        X::loadjson(str, vec, false);
    };
    
    /*
     List数组的增长
     */
    template <typename T>
    static void appendList(list<T> &old_list,list<T> &new_list){
        for(auto item:new_list){
            old_list.push_back(item);
        }
    }
};

class WriterAssistant{
public:
    /*
     csv文件的重写
     */
    static void writeCSV(){
        csv::Writer foo("/Users/sean/Documents/Projects/Packing-Algorithm/record/test.csv");
        // 设置头文件
        foo.configure_dialect()
          .delimiter(", ")
          .column_names("a", "b", "c");
        
        // 需要现转化为String再写入
        for (long i = 0; i < 10; i++) {
            // 可以直接写入
            foo.write_row("1", "2", "3");
            // 也可以按mapping写入
            foo.write_row(map<string, string>{
              {"a", "7"}, {"b", "8"}, {"c", "9"} });
        }
        foo.close();
    };
};
