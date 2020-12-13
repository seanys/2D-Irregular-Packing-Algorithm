"""
该文件实现了拆分算法 Separation去除重叠
和Compaction压缩当前解
-----------------------------------
Created on Wed Dec 11, 2020
@author: seanys,prinway
-----------------------------------
We will update this file soon, now 
it has some wrong.
"""
from tools.geofunc import GeoFunc
from tools.show import PltFunc
from tools.lp import sovleLP,problem
from tools.lp_assistant import LPAssistant
import pandas as pd
import json
from shapely.geometry import Polygon,Point,mapping,LineString
from interval import Interval
import copy
import random
import math
    
class LPFunction(object):
    '''
    参考文献：Solving Irregular Strip Packing problems by hybridising simulated annealing and linear programming
    功能：Compaction与Separation函数处理
    '''
    def __init__(self,polys,poly_status,width,length,_type):
        self._type=_type
        self.all_nfp=pd.read_csv("/Users/sean/Documents/Projects/Data/fu_simplify.csv")
        self.poly_status=copy.deepcopy(poly_status)
        self.polys=copy.deepcopy(polys)
        self.WIDTH=width
        # print("初始高度:",LPAssistant.getLength(polys))
        # self.LENGTH=LPAssistant.getLength(polys)
        # print(LPAssistant.getLength(polys))
        self.LENGTH=length
        self.DISTANCE=400
        self.main()
        
    def main(self):
        # 初始化全部参数，目标参数为z,x1,y1,x2,y...,
        N=len(self.polys)
        if self._type=="separation":
            a,b,c=[[0]*(2*N+N*N) for _ in range(8*N+N*N)],[0 for _ in range(8*N+N*N)],[0 for _ in range(N*2+N*N)]
        else:
            # Compaction有x1-xn/y1-yn/z共2N+1个参数，限制距离和边界2N个限制，N*N个两两间的约束
            a,b,c=[[0]*(2*N+1) for _ in range(9*N+N*N)],[0 for _ in range(9*N+N*N)],[0 for _ in range(N*2+1)]
        
        # 获得常数限制和多边形的限制
        self.getConstants()
        self.getTargetEdges()
        
        # 限制全部移动距离 OK
        for i in range(N):
            row=i*4
            a[row+0][i*2+0],b[row+0]=-1,-self.DISTANCE-self.Xi[i] # -xi>=-DISTANCE-Xi
            a[row+1][i*2+1],b[row+1]=-1,-self.DISTANCE-self.Yi[i] # -yi>=-DISTANCE-Yi
            a[row+2][i*2+0],b[row+2]= 1,-self.DISTANCE+self.Xi[i] # xi>=-DISTANCE+Xi
            a[row+3][i*2+1],b[row+3]= 1,-self.DISTANCE+self.Yi[i] # yi>=-DISTANCE+Yi
        
        # 限制无法移出边界 OK
        for i in range(N):
            row=4*N+i*4
            a[row+0][i*2+0],b[row+0]= 1,self.W_[i] # xi>=Wi*
            a[row+1][i*2+1],b[row+1]= 1,self.H[i]  # yi>=Hi
            a[row+2][i*2+0],b[row+2]=-1,self.W[i]-self.LENGTH  # -xi>=Wi-Length
            a[row+3][i*2+1],b[row+3]=-1,-self.WIDTH  # -yi>=-Width

        # 限制不出现重叠情况 有一点问题
        for i in range(N):
            for j in range(N):
                row=8*N+i*N+j
                if self._type=="separation":
                    if i!=j:
                        a[row][i*2+0],a[row][i*2+1],a[row][j*2+0],a[row][j*2+1],b[row]=self.getOverlapConstrain(i,j)
                        a[row][2*N+i*N+j],c[2*N+i*N+j]=1,1 # 目标函数变化 
                    else:
                        a[row][2*N+i*N+j],c[2*N+i*N+j],b[row]=1,1,0
                else:
                    if i!=j:
                        a[row][i*2+0],a[row][i*2+1],a[row][j*2+0],a[row][j*2+1],b[row]=self.getOverlapConstrain(i,j)
        
        if self._type=="compaction":
            # 大于所有形状的位置+高度，z-xi>=w OK
            for i in range(N):
                row=8*N+N*N+i
                a[row][2*N],a[row][i*2],b[row]=1,-1,self.W[i]
            c[2*N]=1

        # 求解计算结果
        result,self.final_value=sovleLP(a,b,c,_type=self._type)

        # 将其转化为坐标，Variable的输出顺序是[a00,..,ann,x1,..,xn,y1,..,yn]
        placement_points=[]
        if self._type=="separation":
            for i in range(N*N,N*N+N):
                placement_points.append([result[i],result[i+N]])
        else:
            for i in range(len(result)//2):
                placement_points.append([result[i],result[i+N]])
        
        # 获得最终结果
        self.getResult(placement_points)
    
    # 更新最终的结果，更新所有的位置
    def getResult(self,placement_points):
        self.final_polys,self.final_poly_status=[],copy.deepcopy(self.poly_status)
        for i,poly in enumerate(self.polys):
            self.final_polys.append(GeoFunc.getSlide(poly,placement_points[i][0]-self.Xi[i],placement_points[i][1]-self.Yi[i]))
            self.final_poly_status[i][1]=[placement_points[i][0],placement_points[i][1]]

        # for i in range(len(self.polys)):
        #     PltFunc.addPolygon(self.final_polys[i])
        #     PltFunc.addPolygonColor(self.polys[i]) # 初始化的结果
        # PltFunc.showPlt(width=1500,height=1500)
            
    def getOverlapConstrain(self,i,j):
        # 初始化参数
        a_xi,a_yi,a_xj,a_yj,b=0,0,0,0,0
        
        # 获取Stationary Poly的参考点的坐标
        Xi,Yi=self.Xi[i],self.Yi[i] 

        # 获取参考的边
        edge=self.target_edges[i][j] 
        X1,Y1,X2,Y2=edge[0][0],edge[0][1],edge[1][0],edge[1][1]

        '''
        非重叠情况
        式1: (y2-y1)*xj+(x1-x2)*yj+x2*y1-x1*y2>0  右侧距离大于0
        式2: (Y2-Y1)*xj+(X1-X2)*yj+X2*Y1-X1*Y2+(xi-Xi)*(Y1-Y2)+(yi-Yi)*(X2-X1)+>0
        式3: (Y2-Y1)*xj+(X1-X2)*yj+X2*Y1-X1*Y2+(Y1-Y2)*xi+(X2-X1)*yi-Xi*(Y1-Y2)-Yi*(X2-X1)>0
        式4: (Y1-Y2)*xi+(X2-X1)*yi+(Y2-Y1)*xj+(X1-X2)*yj>-X2*Y1+X1*Y2+Xi*(Y1-Y2)+Yi*(X2-X1)
        重叠情况
        式1: -((y2-y1)*xj+(x1-x2)*yj+x2*y1-x1*y2)-a_ij<0  左侧距离小于0
        式2: (y2-y1)*xj+(x1-x2)*yj+x2*y1-x1*y2+a_ij>0
        式1: (Y1-Y2)*xi+(X2-X1)*yi+(Y2-Y1)*xj+(X1-X2)*yj+a_ij>-X2*Y1+X1*Y2+Xi*(Y1-Y2)+Yi*(X2-X1) 左侧距离小于0
        总结: 重叠的时候由于求出来是负值，最终只增加了一个a_ij，参数肯定是1
        '''
        a_xi,a_yi,a_xj,a_yj,b=Y1-Y2,X2-X1,Y2-Y1,X1-X2,-X2*Y1+X1*Y2+Xi*(Y1-Y2)+Yi*(X2-X1)
        
        return a_xi,a_yi,a_xj,a_yj,b
    
    # 获取所有的常数限制
    def getConstants(self):
        self.W=[] # 最高位置到右侧的距离
        self.W_=[] # 最高位置到左侧的距离
        self.H=[] # 最高点
        self.Xi=[] # Xi的初始位置
        self.Yi=[] # Yi的初始位置
        self.PLACEMENTPOINT=[]
        for i,poly in enumerate(self.polys):
            left,bottom,right,top=LPAssistant.getBoundPoint(poly)
            self.PLACEMENTPOINT.append([top[0],top[1]])
            self.Xi.append(top[0])
            self.Yi.append(top[1])
            self.W.append(right[0]-top[0])
            self.W_.append(top[0]-left[0])
            self.H.append(top[1]-bottom[1])
        # print("W:",self.W)
        # print("W_:",self.W_)
        # print("H:",self.H)
        # print("Xi:",self.Xi)
        # print("Yi:",self.Yi)
        # print("PLACEMENTPOINT:",self.PLACEMENTPOINT)
        # print("Length:",self.LENGTH)

    # 获取所有两条边之间的关系
    def getTargetEdges(self):
        self.target_edges=[[0]*len(self.polys) for _ in range(len(self.polys))]
        for i in range(len(self.polys)):
            for j in range(len(self.polys)):
                if i==j:
                    continue
                nfp=self.getNFP(i,j)
                nfp_edges=GeoFunc.getPolyEdges(nfp)
                point=self.PLACEMENTPOINT[j]
                if Polygon(nfp).contains(Point(point)) and self._type=="separation":
                    # 如果包含且是拆分，则寻找距离最近的那个
                    min_distance=99999999999999
                    for edge in nfp_edges:
                        left_distance=-self.getRightDistance(edge,point)
                        if left_distance<=min_distance:
                            min_distance=left_distance
                            self.target_edges[i][j]=copy.deepcopy(edge)
                else:
                    # 如果不包含或者是压缩，则选择最远的
                    max_distance=-0.00001
                    for edge in nfp_edges:
                        right_distance=self.getRightDistance(edge,point)
                        if right_distance>=max_distance:
                            max_distance=right_distance
                            self.target_edges[i][j]=copy.deepcopy(edge)

    @staticmethod
    def getRightDistance(edge,point):
        A=edge[1][1]-edge[0][1]
        B=edge[0][0]-edge[1][0]
        C=edge[1][0]*edge[0][1]-edge[0][0]*edge[1][1]
        D=A*point[0]+B*point[1]+C
        dis=(math.fabs(A*point[0]+B*point[1]+C))/(math.pow(A*A+B*B,0.5))
        if D>0:
            return dis # 右侧返回正
        elif D==0:
            return 0 # 直线上返回0
        else:
            return -dis # 左侧返回负值

    def getNFP(self,j,i):
        # j是固定位置，i是移动位置
        row=j*192+i*16+self.poly_status[j][2]*4+self.poly_status[i][2]
        bottom_pt=LPAssistant.getBottomPoint(self.polys[j])
        delta_x,delta_y=bottom_pt[0],bottom_pt[1]
        nfp=GeoFunc.getSlide(json.loads(self.all_nfp["nfp"][row]),delta_x,delta_y)
        return nfp


def searchForBest(polys,poly_status,width,length):
    # 记录最优结果
    best_poly_status,best_polys=[],[]
    cur_length=length

    # 循环检索最优位置(Polys不需要变化)
    while True:
        print("允许高度:",cur_length)
        result_polys,result_poly_status,result_value=searchOneLength(polys,poly_status,width,cur_length,"separation")
        if result_value==0:
            best_polys=result_polys
            break
        cur_length=cur_length+4
    
    print("开始准确检索")
    # 精准检索最优结果
    for i in range(3):
        cur_length=cur_length-1
        print("允许高度:",cur_length)
        result_polys,result_poly_status,result_value=searchOneLength(polys,poly_status,width,cur_length,"separation")
        if result_value!=0:
            break
        best_polys=result_polys

    best_length=cur_length+1
    print("Separation最终高度:",best_length)

    # 执行Compaction代码更新状态，只有在最后这次才需要改poly_status
    best_polys,best_poly_status,best_length=searchOneLength(best_polys,poly_status,width,best_length,"compaction")

    print("最终高度:",best_length)
    return best_polys,poly_status,best_length


def searchOneLength(polys,poly_status,width,length,_type):
    '''
    检索一个确定高度到不会变化
    Separation: 检索某个高度是否能够达到0，如果不能达到，就返回最终结果、状态、最终重叠
    Compaction: 检索某个高度，返回最终形状、状态、计算高度
    '''
    input_polys=copy.deepcopy(polys) # 每次输入的形状
    last_value=99999999999
    final_polys,final_poly_status=[],[]
    while True:
        res=LPFunction(input_polys,poly_status,width,length,_type)
        # 如果没有重叠，或者等于上一个状态
        if res.final_value==0 or abs(res.final_value-last_value)<0.001:
            last_value=res.final_value
            final_polys=copy.deepcopy(res.final_polys)
            final_poly_status=copy.deepcopy(res.final_poly_status)
            break
        # 如果有变化，则更换状态再试一次
        input_polys=copy.deepcopy(res.final_polys)
        last_value=res.final_value
    return final_polys,final_poly_status,last_value

if __name__ == "__main__":
    blf = pd.read_csv("record/blf.csv")
    index=7
    polys,poly_status,width=json.loads(blf["polys"][index]),json.loads(blf["poly_status"][index]),int(blf["width"][index])

    searchForBest(polys,poly_status,width,628.1533587455999)

    # LPFunction(polys,poly_status,width,628.1533587455999,"compaction")
    # Compaction(polys,poly_status,width)


