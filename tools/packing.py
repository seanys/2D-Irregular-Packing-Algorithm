from tools.nfp import NFP
from shapely.geometry import Polygon,Point,mapping,LineString
from shapely.ops import unary_union
from shapely import affinity
from tools.geofunc import GeoFunc
import pyclipper 
import math
import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt
import csv
import logging
import random
import copy
import os

def getNFP(poly1,poly2): # 这个函数必须放在class外面否则多进程报错
    nfp=NFP(poly1,poly2).nfp
    return nfp


class Poly(object):
    '''
    用于后续的Poly对象
    '''
    def __init__(self,num,poly,allowed_rotation):
        self.num=num
        self.poly=poly
        self.cur_poly=poly
        self.allowed_rotation=[0,180]

class GeoFunc(object):
    '''
    几何相关函数
    1. checkBottom、checkTop、checkLeft、checkRight暂时不考虑多个点
    2. checkBottom和checkLeft均考虑最左下角
    '''
    def almostContain(line,point):
        # 会由于int导致计算偏差！！！！！！
        pt1=[line[0][0],line[0][1]]
        pt2=[line[1][0],line[1][1]]
        point=[point[0],point[1]]

        # 水平直线情况：通过比较两个点和中间点比较
        if abs(pt1[1]-point[1])<bias and abs(pt2[1]-point[1])<bias:
            # print("水平情况")
            if (pt1[0]-point[0])*(pt2[0]-point[0])<0:
                return True
            else:
                return False
    
        # 排除垂直的情况
        if abs(pt1[0]-point[0])<bias and abs(pt2[0]-point[0])<bias:
            # print("垂直情况")
            if (pt1[1]-point[1])*(pt2[1]-point[1])<0:
                return True
            else:
                return False

        if abs(pt1[0]-point[0])<bias or abs(pt2[0]-point[0])<bias or abs(pt1[0]-pt2[0])<bias:
            return False
        
        # 正常情况，计算弧度的差值
        arc1=np.arctan((line[0][1]-line[1][1])/(line[0][0]-line[1][0]))
        arc2=np.arctan((point[1]-line[1][1])/(point[0]-line[1][0]))
        if abs(arc1-arc2)<bias: # 原值0.03，dighe近似平行修正为0.01
            if (point[1]-pt1[1])*(pt2[1]-point[1])>0 and (point[0]-pt1[0])*(pt2[0]-point[0])>0:
                # print("一般情况")
                return True
            else:
                return False
        else:
            return False
    
    def computeInterArea(orginal_inter):
        '''
        计算相交区域的面积
        '''
        inter=mapping(orginal_inter)
        # 一个多边形
        if inter["type"]=="Polygon":
            if len(inter["coordinates"])>0:
                poly=inter["coordinates"][0]
                return Polygon(poly).area
            else: return 0
        if inter["type"]=="MultiPolygon":
            area=0
            for _arr in inter["coordinates"]:
                poly=_arr[0]
                area=area+Polygon(poly).area
            return area
        
        if inter["type"]=="GeometryCollection":
            area=0
            for _arr in inter["geometries"]:
                if _arr["type"]=="Polygon":
                    poly=_arr["coordinates"][0]
                    area=area+Polygon(poly).area
            return area
        return 0

    def checkBottom(poly):
        polyP=Polygon(poly)
        min_y=polyP.bounds[1]
        for index,point in enumerate(poly):
            if point[1]==min_y:
                return index

    def checkTop(poly):
        polyP=Polygon(poly)
        max_y=polyP.bounds[3]
        for index,point in enumerate(poly):
            if point[1]==max_y:
                return index
    
    def checkLeft(poly):
        polyP=Polygon(poly)
        min_x=polyP.bounds[0]
        for index,point in enumerate(poly):
            if point[0]==min_x:
                return index
    
    def checkRight(poly):
        polyP=Polygon(poly)
        max_x=polyP.bounds[2]
        for index,point in enumerate(poly):
            if point[0]==max_x:
                return index

    def checkBound(poly):
        return GeoFunc.checkLeft(poly), GeoFunc.checkBottom(poly), GeoFunc.checkRight(poly), GeoFunc.checkTop(poly)
    
    def checkBoundPt(poly):
        '''获得边界的点'''
        left,bottom,right,top=poly[0],poly[0],poly[0],poly[0]
        for i,pt in enumerate(poly):
            if pt[0]<left[0]:
                left=pt
            if pt[0]>right[0]:
                right=pt
            if pt[1]>top[1]:
                top=pt
            if pt[1]<bottom[1]:
                bottom=pt
        return left,bottom,right,top

    def checkBoundValue(poly):
        '''获得边界的值'''
        left,bottom,right,top=poly[0][0],poly[0][1],poly[0][0],poly[0][1]
        for i,pt in enumerate(poly):
            if pt[0]<left:
                left=pt[0]
            if pt[0]>right:
                right=pt[0]
            if pt[1]>top:
                top=pt[1]
            if pt[1]<bottom:
                bottom=pt[1]
        return left,bottom,right,top

    def slideToPoint(poly,pt1,pt2):
        GeoFunc.slidePoly(poly,pt2[0]-pt1[0],pt2[1]-pt1[1])

    def getSlide(poly,x,y):
        '''
        获得平移后的情况
        '''
        new_vertex=[]
        for point in poly:
            new_point=[point[0]+x,point[1]+y]
            new_vertex.append(new_point)
        return new_vertex

    def slidePoly(poly,x,y):
        for point in poly:
            point[0]=point[0]+x
            point[1]=point[1]+y

    def polyToArr(inter):
        res=mapping(inter)
        _arr=[]
        if res["type"]=="MultiPolygon":
            for poly in res["coordinates"]:
                for point in poly[0]:
                    _arr.append([point[0],point[1]])
        elif res["type"]=="GeometryCollection":
            for item in res["geometries"]:
                if item["type"]=="Polygon":
                    for point in item["coordinates"][0]:
                        _arr.append([point[0],point[1]])
        else:
            if res["coordinates"][0][0]==res["coordinates"][0][-1]:
                for point in res["coordinates"][0][0:-1]:
                    _arr.append([point[0],point[1]])
            else:
                for point in res["coordinates"][0]:
                    _arr.append([point[0],point[1]])
        return _arr

    def normData(poly,num):
        for ver in poly:
            ver[0]=ver[0]*num
            ver[1]=ver[1]*num

    '''近似计算'''
    def crossProduct(vec1,vec2):
        res=vec1[0]*vec2[1]-vec1[1]*vec2[0]
        # 最简单的计算
        if abs(res)<bias:
            return 0
        # 部分情况叉积很大但是仍然基本平行
        if abs(vec1[0])>bias and abs(vec2[0])>bias:
            if abs(vec1[1]/vec1[0]-vec2[1]/vec2[0])<bias:
                return 0
        return res
    
    '''用于touching计算交点 可以与另一个交点计算函数合并'''
    def intersection(line1,line2):
        # 如果可以直接计算出交点
        Line1=LineString(line1)
        Line2=LineString(line2)
        inter=Line1.intersection(Line2)
        if inter.is_empty==False:
            mapping_inter=mapping(inter)
            if mapping_inter["type"]=="LineString":
                inter_coor=mapping_inter["coordinates"][0]
            else:
                inter_coor=mapping_inter["coordinates"]
            return inter_coor

        # 对照所有顶点是否相同
        res=[]
        for pt1 in line1:
            for pt2 in line2:
                if GeoFunc.almostEqual(pt1,pt2)==True:
                    # print("pt1,pt2:",pt1,pt2)
                    res=pt1
        if res!=[]:
            return res

        # 计算是否存在almostContain
        for pt in line1:
            if GeoFunc.almostContain(line2,pt)==True:
                return pt
        for pt in line2:
            if GeoFunc.almostContain(line1,pt)==True:
                return pt
        return []
    
    ''' 主要用于判断是否有直线重合 过于复杂需要重构'''
    def newLineInter(line1,line2):
        vec1=GeoFunc.lineToVec(line1)
        vec2=GeoFunc.lineToVec(line2)
        vec12_product=GeoFunc.crossProduct(vec1,vec2)
        Line1=LineString(line1)
        Line2=LineString(line2)
        inter={
            "length":0,
            "geom_type":None
        }
        # 只有平行才会有直线重叠
        if vec12_product==0:
            # copy避免影响原值
            new_line1=GeoFunc.copyPoly(line1)
            new_line2=GeoFunc.copyPoly(line2)
            if vec1[0]*vec2[0]<0 or vec1[1]*vec2[1]<0:
                new_line2=GeoFunc.reverseLine(new_line2)
            # 如果存在顶点相等，则选择其中一个
            if GeoFunc.almostEqual(new_line1[0],new_line2[0]) or GeoFunc.almostEqual(new_line1[1],new_line2[1]):
                inter["length"]=min(Line1.length,Line2.length)
                inter["geom_type"]='LineString'
                return inter
            # 排除只有顶点相交情况
            if GeoFunc.almostEqual(new_line1[0],new_line2[1]):
                inter["length"]=new_line2[1]
                inter["geom_type"]='Point'
                return inter
            if GeoFunc.almostEqual(new_line1[1],new_line2[0]):
                inter["length"]=new_line1[1]
                inter["geom_type"]='Point'
                return inter
            # 否则判断是否包含
            line1_contain_line2_pt0=GeoFunc.almostContain(new_line1,new_line2[0])
            line1_contain_line2_pt1=GeoFunc.almostContain(new_line1,new_line2[1])
            line2_contain_line1_pt0=GeoFunc.almostContain(new_line2,new_line1[0])
            line2_contain_line1_pt1=GeoFunc.almostContain(new_line2,new_line1[1])
            # Line1直接包含Line2
            if line1_contain_line2_pt0 and line1_contain_line2_pt1:
                inter["length"]=Line1.length
                inter["geom_type"]='LineString'
                return inter
            # Line2直接包含Line1
            if line1_contain_line2_pt0 and line1_contain_line2_pt1:
                inter["length"]=Line2.length
                inter["geom_type"]='LineString'
                return inter
            # 相互包含交点
            if line1_contain_line2_pt0 and line2_contain_line1_pt1:
                inter["length"]=LineString([line2[0],line1[1]]).length
                inter["geom_type"]='LineString'
                return inter
            if line1_contain_line2_pt1 and line2_contain_line1_pt0:
                inter["length"]=LineString([line2[1],line1[0]]).length
                inter["geom_type"]='LineString'
                return inter                
        return inter

    def reverseLine(line):
        pt0=line[0]
        pt1=line[1]
        return [[pt1[0],pt1[1]],[pt0[0],pt0[1]]]

    '''近似计算'''
    def almostEqual(point1,point2):
        if abs(point1[0]-point2[0])<bias and abs(point1[1]-point2[1])<bias:
            return True
        else:
            return False

    def extendLine(line):
        '''
        直线延长
        '''
        pt0=line[0]
        pt1=line[1]
        vect01=[pt1[0]-pt0[0],pt1[1]-pt0[1]]
        vect10=[-vect01[0],-vect01[1]]
        multi=40
        new_pt1=[pt0[0]+vect01[0]*multi,pt0[1]+vect01[1]*multi]
        new_pt0=[pt1[0]+vect10[0]*multi,pt1[1]+vect10[1]*multi]
        return [new_pt0,new_pt1]

    def getArc(line):
        if abs(line[0][0]-line[1][0])<0.01: # 垂直情况
            if line[0][1]-line[1][1]>0:
                return 0.5*math.pi
            else:
                return -0.5*math.pi
        k=(line[0][1]-line[1][1])/(line[0][0]-line[1][0])
        arc=np.arctan(k)
        return arc

    def extendInter(line1,line2):
        '''
        获得延长线的交点
        '''
        line1_extend=GeoFunc.extendLine(line1)
        line2_extend=GeoFunc.extendLine(line2)
        # 排查平行情况
        k1=GeoFunc.getArc(line1_extend)
        k2=GeoFunc.getArc(line2_extend)
        if abs(k1-k2)<0.01:
            return [line1[1][0],line1[1][1]]
        inter=mapping(LineString(line1_extend).intersection(LineString(line2_extend)))
        if inter["type"]=="GeometryCollection" or inter["type"]=="LineString":
            return [line1[1][0],line1[1][1]]
        return [inter["coordinates"][0],inter["coordinates"][1]]

    def twoDec(poly):
        for pt in poly:
            pt[0]=round(pt[0],2)
            pt[1]=round(pt[1],2)

    def similarPoly(poly):
        '''
        求解凸多边形的近似多边形，凹多边形内凹部分额外处理
        '''
        change_len=10
        extend_poly=poly+poly
        Poly=Polygon(poly)
        new_edges=[]
        # 计算直线平移
        for i in range(len(poly)):
            line=[extend_poly[i],extend_poly[i+1]]
            new_line=GeoFunc.slideOutLine(line,Poly,change_len)
            new_edges.append(new_line)
        
        # 计算直线延长线
        new_poly=[]
        new_edges.append(new_edges[0])
        for i in range(len(new_edges)-1):
            inter=GeoFunc.extendInter(new_edges[i],new_edges[i+1])
            new_poly.append(inter)
        
        GeoFunc.twoDec(new_poly) 

        return new_poly

    def slideOutLine(line,Poly,change_len):
        '''
        向外平移直线
        '''
        pt0=line[0]
        pt1=line[1]
        mid=[(pt0[0]+pt1[0])/2,(pt0[1]+pt1[1])/2]
        if pt0[1]!=pt1[1]:
            k=-(pt0[0]-pt1[0])/(pt0[1]-pt1[1]) # 垂直直线情况
            theta=math.atan(k)
            delta_x=1*math.cos(theta)
            delta_y=1*math.sin(theta)
            if Poly.contains(Point([mid[0]+delta_x,mid[1]+delta_y])):
                delta_x=-delta_x
                delta_y=-delta_y
            new_line=[[pt0[0]+change_len*delta_x,pt0[1]+change_len*delta_y],[pt1[0]+change_len*delta_x,pt1[1]+change_len*delta_y]]
            return new_line
        else:
            delta_y=1
            if Poly.contains(Point([mid[0],mid[1]+delta_y])):
                delta_y=-delta_y
            return [[pt0[0],pt0[1]+change_len*delta_y],[pt1[0],pt1[1]+change_len*delta_y]]

    def copyPoly(poly):
        new_poly=[]
        for pt in poly:
            new_poly.append([pt[0],pt[1]])
        return new_poly        

    def pointLineDistance(point, line):
        point_x = point[0]
        point_y = point[1]
        line_s_x = line[0][0]
        line_s_y = line[0][1]
        line_e_x = line[1][0]
        line_e_y = line[1][1]
        if line_e_x - line_s_x == 0:
            return abs(point_x - line_s_x),[line_s_x-point_x,0]
        if line_e_y - line_s_y == 0:
            return abs(point_y - line_s_y),[0,line_s_y-point_y]

        k = (line_e_y - line_s_y) / (line_e_x - line_s_x)
        extend_line=[[point_x-1000,point_y-1000*(-1/k)],[point_x+1000,point_y+1000*(-1/k)]]
        inter=LineString(line).intersection(LineString(extend_line))
        if inter.is_empty==True:
            dis1=math.pow((point_x-line_s_x)*(point_x-line_s_x)+(point_y-line_s_y)*(point_y-line_s_y), 0.5)
            dis2=math.pow((point_x-line_e_x)*(point_x-line_e_x)+(point_y-line_e_y)*(point_y-line_e_y), 0.5)
            if dis1>dis2:
                return dis2,[line_e_x-point_x,line_e_y-point_y]
            else:
                return dis1,[line_s_x-point_x,line_s_y-point_y]
        else:
            pt=GeoFunc.getPt(inter)
            dis=math.pow((point_x-pt[0])*(point_x-pt[0])+(point_y-pt[1])*(point_y-pt[1]), 0.5)
            return dis,[pt[0]-point[0],pt[1]-point[1]]

    def getPt(point):
        mapping_result=mapping(point)
        return [mapping_result["coordinates"][0],mapping_result["coordinates"][1]]

    # 获得某个多边形的边
    def getPolyEdges(poly):
        edges=[]
        for index,point in enumerate(poly):
            if index < len(poly)-1:
                edges.append([poly[index],poly[index+1]])
            else:
                edges.append([poly[index],poly[0]])
        return edges

    def pointPrecisionChange(pt,num):
        return [round(pt[0],num),round(pt[1],num)]
    
    def linePrecisionChange(line,num):
        return [GeoFunc.pointPrecisionChange(line[0],num),GeoFunc.pointPrecisionChange(line[1],num)]
    
    def lineToVec(edge):
        return [edge[1][0]-edge[0][0],edge[1][1]-edge[0][1]]
    
    '''可能需要用近似计算进行封装！！！！！！'''
    def judgePosition(edge1,edge2):
        x1=edge1[1][0]-edge1[0][0]
        y1=edge1[1][1]-edge1[0][1]
        x2=edge2[1][0]-edge2[0][0]
        y2=edge2[1][1]-edge2[0][1]
        res=x1*y2-x2*y1
        right=False
        left=False
        parallel=False
        # print("res:",res)
        if res==0:
            parallel=True
        elif res>0:
            left=True
        else:
            right=True 
        return right,left,parallel


    def getSlideLine(line,x,y):
        new_line=[]
        for pt in line:
            new_line.append([pt[0]+x,pt[1]+y])
        return new_line

    def getCentroid(poly):
        return GeoFunc.getPt(Polygon(poly).centroid)

class PackingUtil(object):
    
    @staticmethod
    def getInnerFitRectangle(poly,x,y):
        left_index,bottom_index,right_index,top_index=GeoFunc.checkBound(poly) # 获得边界
        new_poly=GeoFunc.getSlide(poly,-poly[left_index][0],-poly[bottom_index][1]) # 获得平移后的结果

        refer_pt=[new_poly[top_index][0],new_poly[top_index][1]]
        ifr_width=x-new_poly[right_index][0]
        ifr_height=y-new_poly[top_index][1]

        IFR=[refer_pt,[refer_pt[0]+ifr_width,refer_pt[1]],[refer_pt[0]+ifr_width,refer_pt[1]+ifr_height],[refer_pt[0],refer_pt[1]+ifr_height]]
        return IFR
    
class NFPAssistant(object):
    def __init__(self,polys,**kw):
        self.polys=PolyListProcessor.deleteRedundancy(copy.deepcopy(polys))
        self.area_list,self.first_vec_list,self.centroid_list=[],[],[] # 作为参考
        for poly in self.polys:
            P=Polygon(poly)
            self.centroid_list.append(GeoFunc.getPt(P.centroid))
            self.area_list.append(int(P.area))
            self.first_vec_list.append([poly[1][0]-poly[0][0],poly[1][1]-poly[0][1]])
        self.nfp_list=[[0]*len(self.polys) for i in range(len(self.polys))]
        self.load_history=False
        self.history_path=None
        self.history=None
        if 'history_path' in kw:
            self.history_path=kw['history_path']

        if 'load_history' in kw:
            if kw['load_history']==True:
                # 从内存中加载history 直接传递pandas的df对象 缩短I/O时间
                if 'history' in kw:
                    self.history=kw['history']
                self.load_history=True
                self.loadHistory()
        
        self.store_nfp=False
        if 'store_nfp' in kw:
            if kw['store_nfp']==True:
                self.store_nfp=True
        
        self.store_path=None
        if 'store_path' in kw:
            self.store_path=kw['store_path']

        if 'get_all_nfp' in kw:
            if kw['get_all_nfp']==True and self.load_history==False:
                self.getAllNFP()
        
        if 'fast' in kw: # 为BLF进行多进程优化
            if kw['fast']==True:
                self.res=[[0]*len(self.polys) for i in range(len(self.polys))]
                #pool=Pool()
                for i in range(1,len(self.polys)):
                    for j in range(0,i):
                        # 计算nfp(j,i)
                        #self.res[j][i]=pool.apply_async(getNFP,args=(self.polys[j],self.polys[i]))
                        self.nfp_list[j][i]=GeoFunc.getSlide(getNFP(self.polys[j],self.polys[i]),-self.centroid_list[j][0],-self.centroid_list[j][1])
                # pool.close()
                # pool.join()
                # for i in range(1,len(self.polys)):
                #     for j in range(0,i):
                #         self.nfp_list[j][i]=GeoFunc.getSlide(self.res[j][i].get(),-self.centroid_list[j][0],-self.centroid_list[j][1])

    def loadHistory(self):
        if not self.history:
            if not self.history_path:
                path="record/nfp.csv"
            else:
                path=self.history_path
            df = pd.read_csv(path,header=None)
        else:
            df = self.history
        for index in range(df.shape[0]):
            i=self.getPolyIndex(json.loads(df[0][index]))
            j=self.getPolyIndex(json.loads(df[1][index]))
            if i>=0 and j>=0:
                self.nfp_list[i][j]=json.loads(df[2][index])
        # print(self.nfp_list)
        
    # 获得一个形状的index
    def getPolyIndex(self,target):
        area=int(Polygon(target).area)
        first_vec=[target[1][0]-target[0][0],target[1][1]-target[0][1]]
        area_index=PolyListProcessor.getIndexMulti(area,self.area_list)
        if len(area_index)==1: # 只有一个的情况
            return area_index[0]
        else:
            vec_index=PolyListProcessor.getIndexMulti(first_vec,self.first_vec_list)
            index=[x for x in area_index if x in vec_index]
            if len(index)==0:
                return -1
            return index[0] # 一般情况就只有一个了
    
    # 获得所有的形状
    def getAllNFP(self):
        nfp_multi=False 
        if nfp_multi==True:
            tasks=[(main,adjoin) for main in self.polys for adjoin in self.polys]
            res=pool.starmap(NFP,tasks)
            for k,item in enumerate(res):
                i=k//len(self.polys)
                j=k%len(self.polys)
                self.nfp_list[i][j]=GeoFunc.getSlide(item.nfp,-self.centroid_list[i][0],-self.centroid_list[i][1])
        else:
            for i,poly1 in enumerate(self.polys):
                for j,poly2 in enumerate(self.polys):
                    nfp=NFP(poly1,poly2).nfp
                    #NFP(poly1,poly2).showResult()
                    self.nfp_list[i][j]=GeoFunc.getSlide(nfp,-self.centroid_list[i][0],-self.centroid_list[i][1])
        if self.store_nfp==True:
            self.storeNFP()
    
    def storeNFP(self):
        if self.store_path==None:
            path="/Users/sean/Documents/Projects/Packing-Algorithm/record/nfp.csv"
        else:
            path=self.store_path
        with open(path,"a+") as csvfile:
            writer = csv.writer(csvfile)
            for i in range(len(self.polys)):
                for j in range(len(self.polys)):
                    writer.writerows([[self.polys[i],self.polys[j],self.nfp_list[i][j]]])

    # 输入形状获得NFP
    def getDirectNFP(self,poly1,poly2,**kw):
        if 'index' in kw:
            i=kw['index'][0]
            j=kw['index'][1]
            centroid=GeoFunc.getPt(Polygon(self.polys[i]).centroid)
        else:
            # 首先获得poly1和poly2的ID
            i=self.getPolyIndex(poly1)
            j=self.getPolyIndex(poly2)
            centroid=GeoFunc.getPt(Polygon(poly1).centroid)
        # 判断是否计算过并计算nfp
        if self.nfp_list[i][j]==0:
            nfp=NFP(poly1,poly2).nfp
            #self.nfp_list[i][j]=GeoFunc.getSlide(nfp,-centroid[0],-centroid[1])
            if self.store_nfp==True:
                with open("record/nfp.csv","a+") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerows([[poly1,poly2,nfp]])
            return nfp
        else:
            return GeoFunc.getSlide(self.nfp_list[i][j],centroid[0],centroid[1])

class PolyListProcessor(object):
    @staticmethod
    def getPolyObjectList(polys,allowed_rotation):
        '''
        将Polys和允许旋转的角度转化为poly_lists
        '''
        poly_list=[]
        for i,poly in enumerate(polys):
            poly_list.append(Poly(i,poly,allowed_rotation))
        return poly_list

    @staticmethod
    def getPolysVertices(_list):
        '''排序结束后会影响'''
        polys=[]
        for i in range(len(_list)):
            polys.append(_list[i].poly)
        return polys
    
    @staticmethod
    def getPolysVerticesCopy(_list):
        '''不影响list内的形状'''
        polys=[]
        for i in range(len(_list)):
            polys.append(copy.deepcopy(_list[i].poly))
        return polys

    @staticmethod
    def getPolyListIndex(poly_list):
        index_list=[]
        for i in range(len(poly_list)):
            index_list.append(poly_list[i].num)
        return index_list
    
    @staticmethod
    def getIndex(item,_list):
        for i in range(len(_list)):
            if item==_list[i]:
                return i
        return -1
    
    @staticmethod
    def getIndexMulti(item,_list):
        index_list=[]
        for i in range(len(_list)):
            if item==_list[i]:
                index_list.append(i)
        return index_list

    @staticmethod
    def randomSwap(poly_list,target_id):
        new_poly_list=copy.deepcopy(poly_list)

        swap_with = int(random.random() * len(new_poly_list))
        
        item1 = new_poly_list[target_id]
        item2 = new_poly_list[swap_with]
            
        new_poly_list[target_id] = item2
        new_poly_list[swap_with] = item1
        return new_poly_list

    @staticmethod
    def randomRotate(poly_list,min_angle,target_id):
        new_poly_list=copy.deepcopy(poly_list)

        index = random.randint(0,len(new_poly_list)-1)
        RatotionPoly(min_angle).rotation(new_poly_list[index].poly)
        return new_poly_list

    @staticmethod
    def showPolyList(width,poly_list):
        blf=heuristic.BottomLeftFill(width,PolyListProcessor.getPolysVertices(poly_list))
        blf.showAll()

    @staticmethod
    def deleteRedundancy(_arr):
        new_arr = []
        for item in _arr:
            if not item in new_arr:
                new_arr.append(item)
        return new_arr

    @staticmethod
    def getPolysByIndex(index_list,poly_list):
        choosed_poly_list=[]
        for i in index_list:
            choosed_poly_list.append(poly_list[i])
        return choosed_poly_list

class RatotionPoly():
    def __init__(self,angle):
        self.angle=angle
        self._max=360/angle

    def rotation(self,poly):
        if self._max>1:
            # print("旋转图形")
            rotation_res=random.randint(1,self._max-1)
            Poly=Polygon(poly)
            new_Poly=affinity.rotate(Poly,rotation_res*self.angle)
            mapping_res=mapping(new_Poly)
            new_poly=mapping_res["coordinates"][0]
            for index in range(0,len(poly)):
                poly[index]=[new_poly[index][0],new_poly[index][1]]
        else:
            pass
            # print("不允许旋转")

    def rotation_specific(self,poly,angle=-1):
        '''
        旋转特定角度
        '''
        Poly=Polygon(poly)
        if angle==-1: angle=self.angle
        elif len(angle)>0:
            angle=np.random.choice(angle)
            # print('旋转{}°'.format(angle))
        new_Poly=affinity.rotate(Poly,angle)
        mapping_res=mapping(new_Poly)
        new_poly=mapping_res["coordinates"][0]
        for index in range(0,len(poly)):
            poly[index]=[new_poly[index][0],new_poly[index][1]]

