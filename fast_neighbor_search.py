'''
命名规范：类名全部大写、其他函数首字母小写、变量名全部小写
形状情况：计算NFP、BottomLeftFill等均不能影响原始对象
'''
from tools.geofunc import GeoFunc
from tools.data import getData
from tools.show import PltFunc
from tools.packing import PolyListProcessor,NFPAssistant,BottomLeftFill
import pandas as pd
import json
from shapely.geometry import Polygon,Point,mapping,LineString
from interval import Interval
import copy
import random

precision_error=0.000000001

class FNS():
    '''
    参考资料：2004 Fast neighborhood search for two- and three-dimensional nesting problems
    概述：通过贪婪算法，分别在xy轴平移寻找轴上相交面积最小的位置
    待完成：旋转、需要依次采用水平移动/垂直移动/旋转、收缩的高度降低
    '''
    def __init__(self,polys):
        self.polys = polys # 初始的输入形状
        self.cur_polys=polys # 当前形状
        self.poly_list=[] # 包含具体参数，跟随cur_polys变化
        self.width = 1000
        self.height = 999999999
        self.initial()
        self.main()

    def main(self):
        self.shrink()
        self.showResult(current=True)

        self.guidedLocalSearch()

        for i in range(10):
            self.shrink()
            self.guidedLocalSearch()
        
        self.showResult(current=True)
        
    # 获得初始解和判断角度位置  
    def initial(self):
        blf = BottomLeftFill(self.width,self.cur_polys)
        self.height = blf.length
        self.updatePolyList()

    # 收缩宽度，注意cur_polys和poly_list不一样！！！
    def shrink(self):
        self.new_height = self.height*0.95
        print("收缩边界%s" % self.new_height)
        for poly in self.cur_polys:
            top_index = GeoFunc.checkTop(poly)
            delta = self.new_height-poly[top_index][1]
            # 如果有重叠就平移
            if delta < 0:
                GeoFunc.slidePoly(poly,0,delta)
        self.updatePolyList()
    
    # 展示最终结果
    def showResult(self,**kw):
        if "current" in kw and kw["current"]==True:
            for poly in self.cur_polys:
                PltFunc.addPolygonColor(poly)
            PltFunc.addLine([[0,self.new_height],[self.width,self.new_height]],color="blue")
        if "initial" in kw and kw["initial"]==True:
            for poly in self.polys:
                PltFunc.addPolygon(poly)
            PltFunc.addLine([[0,self.height],[self.width,self.height]],color="blue")
        print(self.polys[0])
        PltFunc.showPlt()
    
    # 获得面积的徒刑
    def overlapCompare(self):
        min_overlap=999999999
        min_t=0
        min_area_t=[]
        for t in self.t_lists:
            overlap=self.getArea(t)
            print("t,overlap:",t,overlap)
            if overlap<min_overlap:
                min_area_t=t
                min_overlap=overlap
        return min_area_t
    
    def getArea(self,t):
        area=0
        for item in self.break_points_list:
            if t>=item[1]:
                area=area+self.getQuadratic(t,item[3][1],item[3][2],item[3][3])
            elif t>=item[0]:
                area=area+self.getQuadratic(t,item[2][1],item[2][2],item[2][3])
            else:
                pass
        return area
    
    # 在水平或者垂直直线上寻找最优位置
    def slideNeighbor(self,poly,_type):
        print("检索类型",_type,"...")
        self.break_points_list=[]
        self.t_lists=[]

        self.getBreakPointList(self.horizontal_positive,self.slide_horizontal_positive,_type,-1)
        self.getBreakPointList(self.horizontal_negative,self.slide_horizontal_negative,_type,-1)
        self.getBreakPointList(self.horizontal_positive,self.slide_horizontal_negative,_type,1)
        self.getBreakPointList(self.horizontal_negative,self.slide_horizontal_positive,_type,1)

        # 计算面积的最合适位置
        self.t_lists=self.chooseFeasible(self.t_lists,_type)
        self.t_lists=self.deleteDuplicated(self.t_lists)
        min_area_t=self.overlapCompare()
        
        print("min_area_t:",min_area_t)
        if abs(min_area_t)<precision_error:
            print("0 未检索到更优位置")
            return False

        # 进行平移位置
        if _type=="vertical":
            GeoFunc.slidePoly(self.cur_polys[self.max_miu_index],0,min_area_t)
        else:
            GeoFunc.slidePoly(self.cur_polys[self.max_miu_index],min_area_t,0)

        # 更新PolyList、正负边、重合情况
        self.updatePolyList()
        self.updateEdgesPN()

        print("1 检索到更优位置")
        self.showResult(current=True)
        return True

    def chooseFeasible(self,_list,_type):
        bounds=Polygon(self.cur_polys[self.max_miu_index]).bounds # min_x min_y max_x max_y
        min_max=[-bounds[0],self.width-bounds[2]]
        if _type=="vertical":
            min_max=[-bounds[1],self.new_height-bounds[3]]
        sorted_list=sorted(_list)
        # 如果超出，那就增加边界的t，以下顺序不能调换
        if sorted_list[-1]>min_max[1]:
            sorted_list.append(min_max[1])
        if sorted_list[0]<min_max[0]:
            sorted_list.append(min_max[0])
        new_list=[]
        for t in sorted_list:
            if t>=min_max[0] and t<=min_max[1]:
                new_list.append(t)
        return new_list

    def deleteDuplicated(self,_list):
        result_list = []
        for item in _list:
            if not item in result_list:
                result_list.append(item)
        return result_list

    # 输入Positive和Negative的边，返回Break Point List
    def getBreakPointList(self,edges,slide_edges,_type,sign):
        for edge in edges:
            for slide_edge in slide_edges:
                res=self.getBreakPoints(edge,slide_edge,_type)
                if res==None:
                    continue
                # 均为Negative或Positive需要为负
                if sign==-1:
                    for ABC in res:
                        for i in range(1,4):
                            ABC[i]=-ABC[i]
                self.t_lists.append(res[0][0])
                self.t_lists.append(res[1][0])
                self.break_points_list.append([res[0][0],res[1][0],res[0],res[1]])

    # 获得水平或垂直平移的情况
    def getBreakPoints(self,edge,slide_edge,_type):
        int_type=0
        if _type=="vertical":
            int_type=1

        # 两条直线四个组合计算
        break_points=[]
        self.getSlideT(slide_edge[0],edge,int_type,1,break_points)
        self.getSlideT(slide_edge[1],edge,int_type,1,break_points)
        self.getSlideT(edge[0],slide_edge,int_type,-1,break_points)
        self.getSlideT(edge[1],slide_edge,int_type,-1,break_points)

        # 必须是有两个交点
        if len(break_points)<2:
            return 
        print(break_points)
        break_points=self.deleteDuplicated(break_points)

        # 开始计算具体参数
        t1=min(break_points[0],break_points[1])
        t2=max(break_points[0],break_points[1])

        sliding_result1=GeoFunc.getSlideLine(slide_edge,t1,0)
        sliding_result2=GeoFunc.getSlideLine(slide_edge,t2,0)
        if _type=="vertical":
            sliding_result1=GeoFunc.getSlideLine(slide_edge,0,t1)
            sliding_result2=GeoFunc.getSlideLine(slide_edge,0,t2)       

        pt1=GeoFunc.intersection(sliding_result1,edge) # 可能为Tuple
        pt2=GeoFunc.intersection(sliding_result2,edge) # 可能为Tuple

        pt3=self.getHoriVerInter(pt1,sliding_result2,int_type)

        ratio=(LineString([pt1,pt2]).length)/(t2-t1) # 两条边的比例
        sin_theta=abs(pt1[1-int_type]-pt2[1-int_type])/(LineString([pt1,pt2]).length) # 直线与水平的角度
        A1=0.5*ratio*sin_theta
        B1=-2*t1*A1
        C1=t1*t1*A1
    
        # 计算A2 B2 C2
        A2=0
        B2=abs(pt1[1-int_type]-pt2[1-int_type]) # 平行四边形的高度
        C2=Polygon([pt1,pt2,pt3]).area-B2*t2 # 三角形面积
        return [[t1,A1,B1,C1],[t2,0,B2,C2]]

    # 获得平移的t值，sign和计算方向相关
    def getSlideT(self,pt,edge,_type,sign,break_points):
        inter=self.getHoriVerInter(pt,edge,_type)
        if len(inter)==0:
            return
        break_points.append((inter[_type]-pt[_type])*sign)

    '''没有考虑不存在的情况/没有考虑直线垂直和水平情况'''
    # 某一点水平或垂直平移后与某直线的交点
    def getHoriVerInter(self,pt,edge,_type):
        upper_pt=edge[1]
        lower_pt=edge[0]
        if edge[0][1-_type]>edge[1][1-_type]:
            upper_pt=edge[0]
            lower_pt=edge[1]
        if pt[1-_type] in Interval(lower_pt[1-_type], upper_pt[1-_type]):
            # 中间的位置比例
            mid=(upper_pt[1-_type]-pt[1-_type])/(upper_pt[1-_type]-lower_pt[1-_type])
            # mid=(upper_pt[_type]-pt[_type])/(upper_pt[_type]-lower_pt[_type])
            # 水平_type=0，计算的也是x即0
            inter=[0,0]
            inter[_type]=upper_pt[_type]-(upper_pt[_type]-lower_pt[_type])*mid
            inter[1-_type]=pt[1-_type]
            return inter
        return []

    # 旋转后的近邻位置
    def rotationNeighbor(self,poly):
        pass
    
    # 获得Positive和Negative的Edges
    def updateEdgesPN(self):
        # 其他形状的边的情况
        self.horizontal_positive=[]
        self.horizontal_negative=[]
        self.vertical_positive=[]
        self.vertical_negative=[]
        for index,item in enumerate(self.poly_list):
            if index!=self.max_miu_index:
                self.appendEdges(self.horizontal_positive,item["horizontal"]["positive"])
                self.appendEdges(self.horizontal_negative,item["horizontal"]["negative"])
                self.appendEdges(self.vertical_positive,item["vertical"]["positive"])
                self.appendEdges(self.vertical_negative,item["vertical"]["negative"])
        # 平移对象的边的情况
        self.slide_horizontal_positive=[]
        self.slide_horizontal_negative=[]
        self.slide_vertical_positive=[]
        self.slide_vertical_negative=[]
        self.appendEdges(self.slide_horizontal_positive,self.poly_list[self.max_miu_index]["horizontal"]["positive"])
        self.appendEdges(self.slide_horizontal_negative,self.poly_list[self.max_miu_index]["horizontal"]["negative"])
        self.appendEdges(self.slide_vertical_positive,self.poly_list[self.max_miu_index]["vertical"]["positive"])
        self.appendEdges(self.slide_vertical_negative,self.poly_list[self.max_miu_index]["vertical"]["negative"])
    
    def appendEdges(self,target,source):
        for edge in source:
            target.append(edge)

    # 寻找最佳位置
    def bestNeighbor(self,poly):
        res=False
        self.updateEdgesPN()
        # 水平移动效果slideNeighbor
        if self.slideNeighbor(poly,"horizontal")==True:
            res=True
        # 垂直移动
        if self.slideNeighbor(poly,"vertical")==True:
            res=True
        # 旋转
        if self.rotationNeighbor(poly)==True:
            res=True

        return res
    
    # 论文 Algorithm1 防止局部最优
    def guidedLocalSearch(self):
        # 初始化的判断参数
        self.phi = [[0]*len(self.cur_polys) for i in range(len(self.cur_polys))] # 惩罚函数
        self.miu_pair=[[0]*len(self.cur_polys) for i in range(len(self.cur_polys))] # 调整后的重叠情况
        self.miu_each=[0 for i in range(len(self.cur_polys))] # 调整后的重叠情况

        # 判断是否有重叠以及寻找最大miu
        self.updateSearchStatus()

        search_times=0

        # 如果有重叠将
        while self.overlap==True and search_times<5:
            # 检索次数限制用于出循环

            print("最大的index为:",self.max_miu_index)
            while self.bestNeighbor(self.cur_polys[self.max_miu_index])==True:
                self.updateSearchStatus()  # 更新并寻找最大Miu
                
            # 更新对应的Phi值并更新Miu
            self.phi[self.max_miu_pair_indx[0]][self.max_miu_pair_indx[0]]+=1
            self.updateSearchStatus()
            print("最大的index更新为:",self.max_miu_index)

            search_times=search_times+1

    # 计算所有形状和其他形状的 Overlap 以及是否没有重叠
    def updateSearchStatus(self):
        # 计算重叠情况
        self.overlap_pair=[[0]*len(self.cur_polys) for i in range(len(self.cur_polys))]
        self.overlap_each=[0 for i in range(len(self.cur_polys))]
        for i in range(0,len(self.cur_polys)-1):
            for j in range(i+1,len(self.cur_polys)):
                Pi=Polygon(self.cur_polys[i])
                Pj=Polygon(self.cur_polys[j])
                overlap_area=GeoFunc.computeInterArea(Pi.intersection(Pj))
                if overlap_area>precision_error:
                    self.overlap_pair[i][j]=self.overlap_pair[i][j]+overlap_area
                    self.overlap_pair[j][i]=self.overlap_pair[i][j]
                    self.overlap_each[i]=self.overlap_each[i]+overlap_area
                    self.overlap_each[j]=self.overlap_each[j]+overlap_area
        
        # 更新是否重叠
        self.overlap=False
        for area in self.overlap_each:
            if area>0:
                self.overlap=True

        # 计算对应的Miu
        max_miu_pair=0
        self.max_miu_pair_indx=[0,0]
        for i in range(0,len(self.cur_polys)):
            for j in range(0,len(self.cur_polys)):
                miu=self.overlap_pair[i][j]/(1+self.phi[i][j])
                self.miu_each[i]=self.miu_each[i]+miu
                if miu>max_miu_pair:
                    self.max_miu_pair_indx=[i,j]
    
        # 获得最大的Miu值
        self.max_miu=0
        self.max_miu_index=-1
        for index,miu in enumerate(self.miu_each):
            if miu>self.max_miu:
                self.max_miu=miu
                self.max_miu_index=index

    # 获得当前所有的边的情况
    def updatePolyList(self):
        self.poly_list=[]
        for i,poly in enumerate(self.cur_polys):
            edges=GeoFunc.getPolyEdges(poly)
            poly_item={
                "index":i,
                "pts":poly,
                "edges":edges,
                "horizontal":{
                    "positive":[],
                    "negative":[],
                    "neutral":[]
                },
                "vertical":{
                    "positive":[],
                    "negative":[],
                    "neutral":[]
                },
            }
            for edge in edges:
                netural=self.judgeNeutral(poly,edge) # 分别获得水平和垂直的计算结果
                for i,cur in enumerate(["horizontal","vertical"]):
                    if netural[i]==1:
                        poly_item[cur]["positive"].append([edge[0],edge[1]])
                    elif netural[i]==-1:
                        poly_item[cur]["negative"].append([edge[0],edge[1]])
                    else:
                        poly_item[cur]["neutral"].append([edge[0],edge[1]])
            self.poly_list.append(poly_item)
        # PltFunc.showPlt()
    
    # 判断是否
    def judgeNeutral(self,poly,edge):
        e=0.000001
        P=Polygon(poly)
        mid=[(edge[0][0]+edge[1][0])/2,(edge[0][1]+edge[1][1])/2]
        positive_contain=[P.contains(Point([mid[0]+e,mid[1]])),P.contains(Point([mid[0],mid[1]+e]))] # 水平移动/垂直移动
        neutral=[1,1] # 水平移动/垂直移动
        for i,contain in enumerate(positive_contain):
            if abs(edge[0][1-i]-edge[1][1-i])<precision_error:
                neutral[i]=0
            elif positive_contain[0]==True:
                neutral[i]=1
            else:
                neutral[i]=-1
        return neutral
    
    def getQuadratic(self,x,A,B,C):
        return A*x*x+B*x+C

class ILSQN():
    '''
    参考资料：2009 An iterated local search algorithm based on nonlinear programming for the irregular strip packing problem
    '''
    def __init__(self,poly_list):
        # 初始设置
        self.width=1500

        # 初始化数据，NFP辅助函数
        polys=PolyListProcessor.getPolysVertices(poly_list)
        self.NFPAssistant=NFPAssistant(polys,get_all_nfp=False)

        # 获得最优解
        blf=BottomLeftFill(self.width,polys,NFPAssistant=self.NFPAssistant)
        self.best_height=blf.contain_height
        self.cur_height=blf.contain_height

        # 当前的poly_list均为已经排样的情况
        self.best_poly_list=copy.deepcopy(poly_list)
        self.cur_poly_list=copy.deepcopy(poly_list)

        self.run()
    
    def run(self):
        for i in range(1):
            if self.minimizeOverlap()==True:
                pass
            else:
                pass
        
    def minimizeOverlap(self):
        k=0
        while k<5:
            initial_solution,height=self.swapTwoPolygons()
            lopt_solution=self.separate(initial_solution)
            pass
    
    def findBestPosition(self):
        pass

    def swapTwoPolygons(self):
        i,j=random.randint(0,len(self.cur_poly_list)-1),random.randint(0,len(self.cur_poly_list)-1)
        pass

    def separate(self):
        pass

if __name__ == "__main__":
    index = 6
    polys = getData(index)
    FNS(polys)
