from geo_func import geoFunc
import pandas as pd
import json

def getData():
    index=0
    '''报错数据集有（空心）：han,jakobs1,jakobs2 '''
    '''形状过多暂时未处理：shapes、shirt、swim、trousers'''
    name=["ga","albano","blaz1","blaz2","dighe1","dighe2","fu","han","jakobs1","jakobs2","mao","marques","shapes","shirts","swim","trousers"]
    print("开始处理",name[index],"数据集")
    '''暂时没有考虑宽度，全部缩放来表示'''
    scale=[100,0.5,100,100,20,20,20,10,20,20,0.5,20,50]
    print("缩放",scale[index],"倍")
    df = pd.read_csv("/Users/sean/Documents/Projects/Packing-Algorithm/euro_data/"+name[index]+".csv")
    polygons=[]
    for i in range(0,df.shape[0]):
        for j in range(0,df['num'][i]):
            poly=json.loads(df['polygon'][i])
            geoFunc.normData(poly,scale[index])
            polygons.append(poly)
    return polygons
