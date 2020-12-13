//
//  data_assistant.hpp
//  Nesting Problem
//
//  Created by Yang Shan on 2020/4/14.
//  Copyright © 2020 Tongji SEM. All rights reserved.

#include <iostream>
#include <string>
#include <vector>
#include <iterator>
#include <math.h>

using namespace std;

// 基础定义
typedef vector<vector<double>> VectorPoints;
typedef vector<vector<vector<double>>> ServalPolygons;

// 形状排样的结果
struct PolysArrange{
    string name=""; // 该数据集的来源
    int type_num=0; // 形状类别总数
    int total_num=0; // 总形状数目
    double width; // 宽度
    double length; // 形状的长度
    double total_area; // 总面积
    vector<vector<vector<double>>> polys; // 所有形状的情况
    vector<vector<double>> polys_position; // 所有形状的顶点位置
    vector<int> polys_type; // 形状对应的关系
    vector<int> polys_orientation; // 所有形状的方向
};

// 输出数组的函数集合
class PrintAssistant{
public:
    /*
    输出一维数组——泛型，暂时统一用double，比如Orientation
    */
    template <typename T>
    static void print1DVector (vector<T> &vec, bool with_endle)
    {
        cout<<"[";
        for (int i=0;i<vec.size();i++){
            cout<<vec[i];
            if(i<(int)vec.size()-1){
                cout<<",";
            }
        }
        cout<<"]";
        if(with_endle==true){
            cout<<endl;
        }
    };
    /*
    输出二维数组——泛型，暂时统一用double，如Positions
    */
    template <typename T>
    static void print2DVector (vector<vector<T>> &vec,bool with_endle)
    {
        cout<<"\"[";
        for (int i=0;i<vec.size();i++){
            print1DVector(vec[i],false);
            if(i<(int)vec.size()-1){
                cout<<",";
            }
        }
        cout<<"]\"";
        if(with_endle==true){
            cout<<endl;
        }
    };
    /*
    输出三维数组——泛型，暂时统一用double，主要是Polygons
    */
    template <typename T>
    static void print3DVector (vector<vector<vector<T>>> &vec,bool with_endle)
    {
        cout<<"[";
        for (int i=0;i<vec.size();i++){
            print2DVector(vec[i],false);
        }
        cout<<"]";
        if(with_endle==true){
            cout<<endl;
        }
    }
};
