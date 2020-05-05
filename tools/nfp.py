from tools.show import PltFunc
from tools.geofunc import GeoFunc
from tools.data import getData
from shapely.geometry import Polygon,Point,mapping,LineString
from shapely.ops import unary_union
import pandas as pd
import json
import copy

class NFP(object):
    def __init__(self,poly1,poly2,**kw):
        self.stationary=copy.deepcopy(poly1)
        self.sliding=copy.deepcopy(poly2)
        start_point_index=GeoFunc.checkBottom(self.stationary)
        self.start_point=[poly1[start_point_index][0],poly1[start_point_index][1]]
        self.locus_index=GeoFunc.checkTop(self.sliding)
        # 如果不加list则original_top是指针
        self.original_top=list(self.sliding[self.locus_index])
        GeoFunc.slideToPoint(self.sliding,self.sliding[self.locus_index],self.start_point)
        self.start=True # 判断是否初始
        self.nfp=[]
        self.rectangle=False
        if 'rectangle' in kw:
            if kw["rectangle"]==True:
                self.rectangle=True
        self.error=1
        self.main()
        if 'show' in kw:
            if kw["show"]==True:
                self.showResult()
        # 计算完成之后平移回原始位置
        GeoFunc.slideToPoint(self.sliding,self.sliding[self.locus_index],self.original_top)

    def main(self):
        i=0
        if self.rectangle: # 若矩形则直接快速运算 点的index为左下角开始逆时针旋转
            width=self.sliding[1][0]-self.sliding[0][0]
            height=self.sliding[3][1]-self.sliding[0][1]
            self.nfp.append([self.stationary[0][0],self.stationary[0][1]])
            self.nfp.append([self.stationary[1][0]+width,self.stationary[1][1]])
            self.nfp.append([self.stationary[2][0]+width,self.stationary[2][1]+height])
            self.nfp.append([self.stationary[3][0],self.stationary[3][1]+height])
        else:
            while self.judgeEnd()==False and i<75: # 大于等于75会自动退出的，一般情况是计算出错
            # while i<7:
                # print("########第",i,"轮##########")
                touching_edges=self.detectTouching()
                all_vectors=self.potentialVector(touching_edges)
                if len(all_vectors)==0:
                    print("没有可行向量")
                    self.error=-2 # 没有可行向量
                    break

                vector=self.feasibleVector(all_vectors,touching_edges)
                if vector==[]:
                    print("没有计算出可行向量")
                    self.error=-5 # 没有计算出可行向量
                    break
                
                self.trimVector(vector)
                if vector==[0,0]:
                    print("未进行移动")
                    self.error=-3 # 未进行移动
                    break

                GeoFunc.slidePoly(self.sliding,vector[0],vector[1])
                self.nfp.append([self.sliding[self.locus_index][0],self.sliding[self.locus_index][1]])
                i=i+1
                inter=Polygon(self.sliding).intersection(Polygon(self.stationary))
                if GeoFunc.computeInterArea(inter)>1:
                    print("出现相交区域")
                    self.error=-4 # 出现相交区域
                    break                

        if i==75:
            print("超出计算次数")
            self.error=-1 # 超出计算次数
    
    # 检测相互的连接情况
    def detectTouching(self):
        touch_edges=[]
        stationary_edges,sliding_edges=self.getAllEdges()
        for edge1 in stationary_edges:
            for edge2 in sliding_edges:
                inter=GeoFunc.intersection(edge1,edge2)
                if inter!=[]:
                    pt=[inter[0],inter[1]] # 交叉点
                    edge1_bound=(GeoFunc.almostEqual(edge1[0],pt) or GeoFunc.almostEqual(edge1[1],pt)) # 是否为边界
                    edge2_bound=(GeoFunc.almostEqual(edge2[0],pt) or GeoFunc.almostEqual(edge2[1],pt)) # 是否为边界
                    stationary_start=GeoFunc.almostEqual(edge1[0],pt) # 是否开始
                    orbiting_start=GeoFunc.almostEqual(edge2[0],pt) # 是否开始
                    touch_edges.append({
                        "edge1":edge1,
                        "edge2":edge2,
                        "vector1":self.edgeToVector(edge1),
                        "vector2":self.edgeToVector(edge2),
                        "edge1_bound":edge1_bound,
                        "edge2_bound":edge2_bound,
                        "stationary_start":stationary_start,
                        "orbiting_start":orbiting_start,
                        "pt":[inter[0],inter[1]],
                        "type":0
                    })
        return touch_edges 

    # 获得潜在的可转移向量
    def potentialVector(self,touching_edges):
        all_vectors=[]
        for touching in touching_edges:
            # print("touching:",touching)
            aim_edge=[]
            # 情况1
            if touching["edge1_bound"]==True and touching["edge2_bound"]==True:
                right,left,parallel=GeoFunc.judgePosition(touching["edge1"],touching["edge2"])
                # print("right,left,parallel:",right,left,parallel)
                if touching["stationary_start"]==True and touching["orbiting_start"]==True:
                    touching["type"]=0
                    if left==True:
                        aim_edge=[touching["edge2"][1],touching["edge2"][0]] # 反方向
                    if right==True:
                        aim_edge=touching["edge1"]
                if touching["stationary_start"]==True and touching["orbiting_start"]==False:
                    touching["type"]=1
                    if left==True:
                        aim_edge=touching["edge1"]
                if touching["stationary_start"]==False and touching["orbiting_start"]==True:
                    touching["type"]=2
                    if right==True:
                        aim_edge=[touching["edge2"][1],touching["edge2"][0]] # 反方向
                if touching["stationary_start"]==False and touching["orbiting_start"]==False:
                    touching["type"]=3
    
            # 情况2
            if touching["edge1_bound"]==False and touching["edge2_bound"]==True:
                aim_edge=[touching["pt"],touching["edge1"][1]]
                touching["type"]=4
            
            # 情况3
            if touching["edge1_bound"]==True and touching["edge2_bound"]==False:
                aim_edge=[touching["edge2"][1],touching["pt"]]
                touching["type"]=5

            if aim_edge!=[]:
                vector=self.edgeToVector(aim_edge)
                if self.detectExisting(all_vectors,vector)==False: # 删除重复的向量降低计算复杂度
                    all_vectors.append(vector)
        return all_vectors
    
    def detectExisting(self,vectors,judge_vector):
        for vector in vectors:
            if GeoFunc.almostEqual(vector,judge_vector):
                return True
        return False
    
    def edgeToVector(self,edge):
        return [edge[1][0]-edge[0][0],edge[1][1]-edge[0][1]]
    
    # 选择可行向量
    def feasibleVector(self,all_vectors,touching_edges):
        '''
        该段代码需要重构，过于复杂
        '''
        res_vector=[]
        # print("\nall_vectors:",all_vectors)
        for vector in all_vectors:
            feasible=True
            # print("\nvector:",vector,"\n")
            for touching in touching_edges:
                vector1=[]
                vector2=[]
                # 判断方向并进行转向
                if touching["stationary_start"]==True:
                    vector1=touching["vector1"]
                else:
                    vector1=[-touching["vector1"][0],-touching["vector1"][1]]
                if touching["orbiting_start"]==True:
                    vector2=touching["vector2"]
                else:
                    vector2=[-touching["vector2"][0],-touching["vector2"][1]]
                vector12_product=GeoFunc.crossProduct(vector1,vector2) # 叉积，大于0在左侧，小于0在右侧，等于0平行
                vector_vector1_product=GeoFunc.crossProduct(vector1,vector) # 叉积，大于0在左侧，小于0在右侧，等于0平行
                vector_vector2_product=GeoFunc.crossProduct(vector2,vector) # 叉积，大于0在左侧，小于0在右侧，等于0平行
                # 最后两种情况
                if touching["type"]==4 and (vector_vector1_product*vector12_product)<0:
                    feasible=False
                if touching["type"]==5 and (vector_vector2_product*(-vector12_product))>0:
                    feasible=False
                # 正常的情况处理
                if vector12_product>0:
                    if vector_vector1_product<0 and vector_vector2_product<0:
                        feasible=False
                if vector12_product<0:
                    if vector_vector1_product>0 and vector_vector2_product>0:
                        feasible=False
                # 平行情况，需要用原值逐一判断
                if vector12_product==0:
                    inter=GeoFunc.newLineInter(touching["edge1"],touching["edge2"])
                    if inter["geom_type"]=="LineString":
                        if inter["length"]>0.01:
                            # 如果有相交，则需要在左侧
                            if (touching["orbiting_start"]==True and vector_vector2_product<0) or (touching["orbiting_start"]==False and vector_vector2_product>0):
                                feasible=False
                    else:
                        # 如果方向相同，且转化直线也平行，则其不能够取a的方向
                        if touching["orbiting_start"]==True != touching["stationary_start"]==False and vector_vector1_product==0:
                            if touching["vector1"][0]*vector[0]>0: # 即方向相同
                                feasible=False
            if feasible==True:
                res_vector=vector
                break
        return res_vector
        
    # 削减过长的向量
    def trimVector(self,vector):
        stationary_edges,sliding_edges=self.getAllEdges()
        new_vectors=[]
        for pt in self.sliding:
            for edge in stationary_edges:
                line_vector=LineString([pt,[pt[0]+vector[0],pt[1]+vector[1]]])
                end_pt=[pt[0]+vector[0],pt[1]+vector[1]]
                line_polygon=LineString(edge)
                inter=line_vector.intersection(line_polygon)
                if inter.geom_type=="Point":
                    inter_mapping=mapping(inter)
                    inter_coor=inter_mapping["coordinates"]
                    if (abs(end_pt[0]-inter_coor[0])>0.01 or abs(end_pt[1]-inter_coor[1])>0.01) and (abs(pt[0]-inter_coor[0])>0.01 or abs(pt[1]-inter_coor[1])>0.01):
                        new_vectors.append([inter_coor[0]-pt[0],inter_coor[1]-pt[1]])

        for pt in self.stationary:
            for edge in sliding_edges:
                line_vector=LineString([pt,[pt[0]-vector[0],pt[1]-vector[1]]])
                end_pt=[pt[0]-vector[0],pt[1]-vector[1]]
                line_polygon=LineString(edge)
                inter=line_vector.intersection(line_polygon)
                if inter.geom_type=="Point":
                    inter_mapping=mapping(inter)
                    inter_coor=inter_mapping["coordinates"]
                    if (abs(end_pt[0]-inter_coor[0])>0.01 or abs(end_pt[1]-inter_coor[1])>0.01) and (abs(pt[0]-inter_coor[0])>0.01 or abs(pt[1]-inter_coor[1])>0.01):
                        new_vectors.append([pt[0]-inter_coor[0],pt[1]-inter_coor[1]])
        
        # print(new_vectors)
        for vec in new_vectors:
            if abs(vec[0])<abs(vector[0]) or abs(vec[1])<abs(vector[1]):
                # print(vec)
                vector[0]=vec[0]
                vector[1]=vec[1]
    
    # 获得两个多边形全部边
    def getAllEdges(self):
        return GeoFunc.getPolyEdges(self.stationary),GeoFunc.getPolyEdges(self.sliding)
    
    # 判断是否结束
    def judgeEnd(self):
        sliding_locus=self.sliding[self.locus_index]
        main_bt=self.start_point
        if abs(sliding_locus[0]-main_bt[0])<0.1 and abs(sliding_locus[1]-main_bt[1])<0.1:
            if self.start==True:
                self.start=False
                # print("判断是否结束：否")
                return False
            else:
                # print("判断是否结束：是")
                return True
        else:
            # print("判断是否结束：否")
            return False

    # 显示最终结果
    def showResult(self):
        PltFunc.addPolygon(self.sliding)
        PltFunc.addPolygon(self.stationary)
        PltFunc.addPolygonColor(self.nfp)
        PltFunc.showPlt()

    # 计算渗透深度
    def getDepth(self):
        '''
        计算poly2的checkTop到NFP的距离
        Source: https://stackoverflow.com/questions/36972537/distance-from-point-to-polygon-when-inside
        '''
        d1=Polygon(self.nfp).distance(Point(self.original_top))
        # if point in inside polygon, d1=0
        # d2: distance from the point to nearest boundary
        if d1==0:
            d2=Polygon(self.nfp).boundary.distance(Point(self.original_top))
            # print('d2:',d2)
            return d2
        else: 
            return 0


