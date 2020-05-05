'''
封装部分协助进行LP计算的函数
'''
from shapely.geometry import Polygon,Point,mapping,LineString
from tools.geofunc import GeoFunc
import math

bias=0.0000001

class LPAssistant(object):
    @staticmethod
    def getConvexPoly(poly):
        Poly=Polygon(poly)
        extend_poly,convex_poly=poly+poly,[]
        # 去除所有的凹点
        for i in range(len(poly)):
            pt1,pt2,pt3=extend_poly[i],extend_poly[i+1],extend_poly[i+2]
            vec=LPAssistant.getAngularBisector(pt1,pt2,pt3)
            if Poly.contains(Point([pt2[0]+vec[0]*0.1,pt2[1]+vec[1]*0.1])):
                convex_poly.append(pt2)
        return convex_poly

    @staticmethod
    def getAngularBisector(pt1,pt2,pt3):
        '''
        输入：pt1/pt3为左右两个点，pt2为中间的点
        输出：该角的对角线
        '''
        vec1=LPAssistant.getDirectionalVector([pt1[0]-pt2[0],pt1[1]-pt2[1]])
        vec2=LPAssistant.getDirectionalVector([pt3[0]-pt2[0],pt3[1]-pt2[1]])
        bisector=[]
        bisector=[(vec1[0]+vec2[0]),vec1[1]+vec2[1]] # 获得对角方向，长度为sqrt(2)
        return bisector

    @staticmethod
    def getDirectionalVector(vec):
        _len=math.sqrt(vec[0]*vec[0]+vec[1]*vec[1])
        return [vec[0]/_len,vec[1]/_len]

    @staticmethod
    def deleteOnline(poly):
        '''删除两条直线在一个延长线情况'''
        new_poly=[]
        for i in range(-2,len(poly)-2):
            vec1=LPAssistant.getDirectionalVector([poly[i+1][0]-poly[i][0],poly[i+1][1]-poly[i][1]])
            vec2=LPAssistant.getDirectionalVector([poly[i+2][0]-poly[i+1][0],poly[i+2][1]-poly[i+1][1]])
            if abs(vec1[0]-vec2[0])>bias or abs(vec1[1]-vec2[1])>bias:
                new_poly.append(poly[i+1])
        return new_poly

    @staticmethod
    def getDividedNfp(nfp):
        all_bisectior,divided_nfp,target_func=[],[],[]
        # 遍历NFP的所有顶点计算角平分线
        for i in range(-2,len(nfp)-2):
            vec=LPAssistant.getAngularBisector(nfp[i],nfp[i+1],nfp[i+2])
            all_bisectior.append([nfp[i+1],[nfp[i+1][0]+vec[0]*1000,nfp[i+1][1]+vec[1]*1000]])

        # 计算全部的三角形区域和附带边
        divided_nfp,target_func=[],[]
        for i in range(-1,len(all_bisectior)-1):
            line1,line2=all_bisectior[i],all_bisectior[i+1]
            inter=LPAssistant.lineIntersection(line1,line2)
            divided_nfp.append([nfp[i-1],nfp[i],inter]) # [边界点1,边界点2,交点]
            target_func.append(LPAssistant.getTargetFunction([nfp[i-1],nfp[i]]))

        return all_bisectior,divided_nfp,target_func

    @staticmethod
    def lineIntersection(line1, line2):
        xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
        ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1]) #Typo was here

        def det(a, b):
            return a[0] * b[1] - a[1] * b[0]

        div = det(xdiff, ydiff)
        if div == 0:
            raise Exception('lines do not intersect')

        d = (det(*line1), det(*line2))
        x = det(d, xdiff) / div
        y = det(d, ydiff) / div
        return [x, y]

    @staticmethod
    def getTargetFunction(edge):
        '''处理NFP拆分的结果，第一条边为边界，只与距离的绝对值有关'''
        A=edge[0][1]-edge[1][1]
        B=edge[1][0]-edge[0][0]
        C=edge[0][0]*edge[1][1]-edge[1][0]*edge[0][1]
        D=math.pow(A*A+B*B,0.5)
        a,b,c=A/D,B/D,C/D
        return [a,b,c]

    @staticmethod
    def getTopPoint(poly):
        top_pt,max_y=[],-999999999
        for pt in poly:
            if pt[1]>max_y:
                max_y=pt[1]
                top_pt=[pt[0],pt[1]]
        return top_pt

    @staticmethod
    def getBottomPoint(poly):
        bottom_pt,min_y=[],999999999
        for pt in poly:
            if pt[1]<min_y:
                min_y=pt[1]
                bottom_pt=[pt[0],pt[1]]
        return bottom_pt

    @staticmethod
    def getRightPoint(poly):
        right_pt,max_x=[],-999999999
        for pt in poly:
            if pt[0]>max_x:
                max_x=pt[0]
                right_pt=[pt[0],pt[1]]
        return right_pt

    @staticmethod
    def getLeftPoint(poly):
        left_pt,min_x=[],999999999
        for pt in poly:
            if pt[0]<min_x:
                min_x=pt[0]
                left_pt=[pt[0],pt[1]]
        return left_pt

    @staticmethod
    def getBottomLeftPoint(poly):
        bottom_left_pt,min_x,min_y=[],999999999,999999999
        for pt in poly:
            if pt[0]<=min_x and pt[1]<=min_y:
                min_x,min_y=pt[0],pt[1]
                bottom_left_pt=[pt[0],pt[1]]
        return bottom_left_pt

    @staticmethod
    def getBoundPoint(poly):
        left_pt,bottom_pt,right_pt,top_pt=[],[],[],[]
        min_x,min_y,max_x,max_y=999999999,999999999,-999999999,-999999999
        for pt in poly:
            if pt[0]<min_x:
                min_x=pt[0]
                left_pt=[pt[0],pt[1]]
            if pt[0]>max_x:
                max_x=pt[0]
                right_pt=[pt[0],pt[1]]
            if pt[1]>max_y:
                max_y=pt[1]
                top_pt=[pt[0],pt[1]]
            if pt[1]<min_y:
                min_y=pt[1]
                bottom_pt=[pt[0],pt[1]]
        return left_pt,bottom_pt,right_pt,top_pt
    
    @staticmethod
    def getFootPoint(point, line_p1, line_p2):
        """
        @point, line_p1, line_p2 : [x, y, z]
        """
        x0 = point[0]
        y0 = point[1]
    
        x1 = line_p1[0]
        y1 = line_p1[1]
    
        x2 = line_p2[0]
        y2 = line_p2[1]
    
        k = -((x1 - x0) * (x2 - x1) + (y1 - y0) * (y2 - y1)) / ((x2 - x1) ** 2 + (y2 - y1) ** 2)*1.0
    
        xn = k * (x2 - x1) + x1
        yn = k * (y2 - y1) + y1
    
        return (xn, yn)
    
    @staticmethod
    def rotationVectorAnti(vec):
        [x,y]=vec
        # 坐标轴情况
        if x==0:
            return [-y,0]
        if y==0:
            return [0,-x]
        # 其他情况
        return [-y,x]

    @staticmethod
    def rotationVector(vec):
        [x,y]=vec
        # 坐标轴情况
        if x==0:
            return [y,0]
        if y==0:
            return [0,-x]
        # 其他情况
        return [y,-x]

    @staticmethod
    def deleteTarget(_list,target):
        new_list=[]
        for item in _list:
            existing=False
            if item not in target:
                new_list.append(item)
        return new_list

    @staticmethod
    def deleteTargetFirst(_list,target):
        new_list=[]
        for item in _list:
            existing=False
            for target_item in target:
                if item[0]==target_item:
                    existing=True
            if existing==False:
                new_list.append(item)
        return new_list

    @staticmethod
    def processRegion(region):
        area=[]
        if region.geom_type=="Polygon":
            area=GeoFunc.polyToArr(region)  # 最终结果只和顶点相关
        else:
            for shapely_item in list(region):
                if shapely_item.area>bias:
                    area=area+GeoFunc.polyToArr(shapely_item)
        return area    

    @staticmethod
    def getLength(polys):
        _max=0
        for i in range(0,len(polys)):
            [x,y]=LPAssistant.getRightPoint(polys[i])
            if x>_max:
                _max=x
        return _max

    @staticmethod
    def judgeFeasible(polys):
        for i in range(len(polys)-1):
            for j in range(i+1,len(polys)):
                P1,P2=Polygon(polys[i]),Polygon(polys[j])
                if P1.intersection(P2).area>bias:
                    return False
        return True
    
    @staticmethod
    def delEmpty(target_areas):
        new_target_areas=[]
        for line in target_areas:
            new_target_areas.append([item for item in line if item])
        return new_target_areas