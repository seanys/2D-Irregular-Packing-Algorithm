'''
封装部分协助进行LP计算的函数
'''
from shapely.geometry import Polygon,Point,mapping,LineString
from tools.geofunc import GeoFunc
from math import sqrt,acos
import math

bias=0.0000001


class GeometryAssistant(object):
    '''
    几何相关的算法重新统一
    '''
    @staticmethod
    def getAdjustPts(original_points, first_pt, to_real):
        '''部分情况需要根据相对位置调整范围'''
        new_points = []
        for pt in original_points:
            if to_real == True:
                new_points.append([pt[0] + first_pt[0],pt[1] + first_pt[1]])
            else:
                new_points.append([pt[0] - first_pt[0],pt[1] - first_pt[1]])
        return new_points

    @staticmethod
    def judgeContain(pt,parts):
        '''判断点是否包含在NFP凸分解后的凸多边形列表中 输入相对位置点'''
        def cross(p0,p1,p2):
            '''计算叉乘'''
            return (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])

        for part in parts: # 对凸多边形逐个判断
            n=len(part)
            if cross(part[0],pt,part[1])>bias or cross(part[0],pt,part[n-1])<-bias:
                continue
            i=1
            j=n-1
            line=-1
            while i<=j:
                mid=int((i+j)/2)
                if cross(part[0],pt,part[mid])>0:
                    line=mid
                    j=mid-1
                else:
                    i=mid+1
            if cross(part[line-1],pt,part[line])<bias:
                return True
        return False

    @staticmethod
    def getPtNFPPD(pt, convex_status, nfp, pd_bias):
        '''根据最终属性求解PD'''
        min_pd, edges = 999999999, GeometryAssistant.getPolyEdges(nfp)
        last_num = 4 # 最多求往后的3条边
        for k in range(len(edges)):
            # 求解直线边界PD
            nfp_pt, edge = nfp[k], edges[k]
            foot_pt = GeometryAssistant.getFootPoint(pt,edge[0],edge[1]) # 求解垂足
            if GeometryAssistant.bounds(foot_pt[0], edge[0][0], edge[1][0]) == False or GeometryAssistant.bounds(foot_pt[1], edge[0][1], edge[1][1]) == False:
                continue
            pd = sqrt(pow(foot_pt[0]-pt[0],2) + pow(foot_pt[1]-pt[1],2))
            if pd < min_pd:
                min_pd = pd 
            # 求解凹点PD
            if convex_status[k] == 0:
                non_convex_pd = abs(pt[0]-nfp_pt[0]) + abs(pt[1]-nfp_pt[1])
                if non_convex_pd < min_pd:
                    min_pd = non_convex_pd
            # 如果开启了凹点
            if min_pd < 20:
                last_num = last_num - 1
            if last_num == 0:
                break
            # 判断是否为0（一般不会出现该情况）
            if min_pd < pd_bias:
                return 0
        return min_pd

    @staticmethod
    def bounds(val, bound0, bound1):
        if min(bound0, bound1) - bias <= val <= max(bound0, bound1) + bias:
            return True
        else:
            return False

    @staticmethod
    def getLineCoe(line):
        x1, y1, x2, y2 = line[0][0], line[0][1], line[1][0], line[1][1]
        k = (y2 - y1)/(x2 - x1)
        b = y1 - k*x1
        return k, b

    @staticmethod
    def parallelInter(line1, line2):
        # 判断是否水平，水平用x做参考，其他用y
        k = 1
        if line1[0][1] == line1[1][1] or line2[0][1] == line2[1][1]:
            k = 0
        # 第一个点的包含（不考虑为点）
        if GeometryAssistant.bounds(line1[0][k], line2[0][k], line2[1][k]) == True:
            if GeometryAssistant.bounds(line1[1][k], line2[0][k], line2[1][k]) == True:
                return [line1[0], line1[1]], True # 返回中间的直线
            else:
                if GeometryAssistant.bounds(line2[0][k], line1[0][k], line1[1][k]) == True:
                    return [line1[0], line2[0]], True
                else:
                    return [line1[0], line2[1]], True

        # 没有包含第一个点，判断第二个
        if GeometryAssistant.bounds(line1[1][k], line2[0][k], line2[1][k]) == True:
            if GeometryAssistant.bounds(line2[0][k], line1[0][k], line1[1][k]) == True:
                return [line1[1], line2[0]], True
            else:
                return [line1[1], line2[1]], True

        # Vectical没有包含Line的两个点
        if GeometryAssistant.bounds(line2[0][k], line1[0][k], line1[1][k]) == True:
            return [line2[0], line2[1]], True
        else:
            return [], False

    @staticmethod
    def verticalInter(ver_line, line):
        # 如果另一条直线也垂直
        if abs(line[0][0] - line[1][0]) < bias:
            if abs(line[0][0] - ver_line[0][0]):
                return GeometryAssistant.parallelInter(line, ver_line)
            else:
                return [], False
        # 否则求解直线交点
        k, b = GeometryAssistant.getLineCoe(line)
        x = ver_line[0][0]
        y = k * x + b
        # print(k, b)
        # print(x, y)
        if GeometryAssistant.bounds(y, ver_line[0][1], ver_line[1][1]):
            return [[x,y]], True
        else:
            return [], False

    @staticmethod
    def lineInter(line1, line2):
        if min(line1[0][0],line1[1][0]) > max(line2[0][0],line2[1][0]) or max(line1[0][0],line1[1][0]) < min(line2[0][0],line2[1][0]) or min(line1[0][1],line1[1][1]) > max(line2[0][1],line2[1][1]) or max(line1[0][1],line1[1][1]) < min(line2[0][1],line2[1][1]):
            return [], False
        # 为点的情况（例外）
        if line1[0] == line1[1] or line2[0] == line2[1]:
            return [], False
        # 出现直线垂直的情况（没有k）
        if abs(line1[0][0] - line1[1][0]) < bias:
            return GeometryAssistant.verticalInter(line1,line2)
        if abs(line2[0][0] - line2[1][0]) < bias:
            return GeometryAssistant.verticalInter(line2,line1)
        # 求解y=kx+b
        k1, b1 = GeometryAssistant.getLineCoe(line1)
        k2, b2 = GeometryAssistant.getLineCoe(line2)
        if k1 == k2:
            if b1 == b2:
                return GeometryAssistant.parallelInter(line1, line2)
            else:
                return [], False
        # 求直线交点
        x = (b2 - b1)/(k1 - k2)
        y = k1 * x + b1
        if GeometryAssistant.bounds(x, line1[0][0], line1[1][0]) and GeometryAssistant.bounds(x, line2[0][0], line2[1][0]):
            return [[x,y]], True
        return [], False
    
    @staticmethod
    def getPointsContained(inter_points, ifr_bounds):
        new_points = []
        for pt in inter_points:
            if GeometryAssistant.boundsContain(ifr_bounds, pt):
                new_points.append(pt)
        return new_points
    
    @staticmethod
    def interBetweenNFPs(nfp1_edges, nfp2_edges, bounds1, bounds2):
        '''计算直线交点，仅考虑'''
        inter_points, intersects = [], False
        for edge1 in nfp1_edges:
            if max(edge1[0][0],edge1[1][0]) < bounds2[0] or min(edge1[0][0],edge1[1][0]) > bounds2[2] \
                or max(edge1[0][1],edge1[1][1]) < bounds2[1] or min(edge1[0][1],edge1[1][1]) > bounds2[3]:
                continue
            for edge2 in nfp2_edges:
                if max(edge2[0][0],edge2[1][0]) < bounds1[0] and min(edge2[0][0],edge2[1][0]) > bounds1[2] \
                    or max(edge2[0][1],edge2[1][1]) < bounds1[1] and min(edge2[0][1],edge2[1][1]) > bounds1[3]:
                    continue
                pts, inter_or = GeometryAssistant.lineInter(edge1, edge2)
                if inter_or == False:
                    continue
                intersects = True # 只要有直线交点全部认为是
                for pt in pts:
                    # print(pt, edge1, edge2)
                    if [pt[0],pt[1]] not in inter_points:
                        inter_points.append([pt[0],pt[1]])
        return inter_points, intersects

    @staticmethod
    def interNFPIFR(nfp, ifr_bounds, ifr_edges, ifr):
        '''求解NFP与IFR的相交区域'''
        total_points, border_pts, inside_indexs = [], [], [] # NFP在IFR内部的点及交，计算参考和边界可行范围
        contain_last, contain_this = False, False
        temp_nfp = nfp + [nfp[0]]
        for i, pt in enumerate(temp_nfp):
            # 第一个点
            if i == 0:
                if GeometryAssistant.boundsContain(ifr_bounds, pt) == True:
                    inside_indexs.append(i)
                    total_points.append([pt[0], pt[1]])
                    contain_last = True
                continue
            # 后续的点求解
            if GeometryAssistant.boundsContain(ifr_bounds, pt) == True:
                if i != len(temp_nfp) - 1:
                    inside_indexs.append(i)
                    total_points.append([pt[0], pt[1]])
                contain_this = True
            else:
                contain_this = False
            # 只有两个不全在内侧的时候才需要计算交点
            if contain_last == False or contain_this == False:
                for k,edge in enumerate(ifr_edges):
                    inter_pts, inter_or = GeometryAssistant.lineInter([temp_nfp[i-1],temp_nfp[i]], edge)
                    if inter_or == True:
                        for new_pt in inter_pts:
                            if new_pt not in total_points:
                                total_points.append(new_pt) # 将交点加入可行点
                                border_pts.append(new_pt) # 将交点加入可行点
            contain_last = contain_this
        return total_points, inside_indexs, border_pts
    
    @staticmethod
    def addRelativeRecord(record_target, target_key, inside_indexs, border_pts, first_pt):
        adjust_border_pts = GeometryAssistant.getAdjustPts(border_pts, first_pt, False)
        record_target[target_key] = {}
        record_target[target_key]["adjust_border_pts"] = adjust_border_pts
        record_target[target_key]["inside_indexs"] = inside_indexs

    @staticmethod
    def addAbsoluteRecord(record_target, target_key, inside_indexs, border_pts):
        record_target[target_key] = {}
        record_target[target_key]["border_pts"] = border_pts
        record_target[target_key]["inside_indexs"] = inside_indexs

    @staticmethod
    def boundsContain(bounds, pt):
        if pt[0] >= bounds[0] and pt[0] <= bounds[2] and pt[1] >= bounds[1] and pt[1] <= bounds[3]:
            return True
        return False
        
    @staticmethod
    def getPolysRight(polys):
        _max=0
        for i in range(0,len(polys)):
            [x,y] = GeometryAssistant.getRightPoint(polys[i])
            if x > _max:
                _max=x
        return _max

    @staticmethod
    def kwtGroupToArray(kwt_group, judge_area):
        '''将几何对象转化为数组，以及是否判断面积大小'''
        array = []
        if kwt_group.geom_type == "Polygon":
            array = GeometryAssistant.kwtItemToArray(kwt_group, judge_area)  # 最终结果只和顶点相关
        else:
            for shapely_item in list(kwt_group):
                array = array + GeometryAssistant.kwtItemToArray(shapely_item,judge_area)
        return array   

    @staticmethod
    def kwtItemToArray(kwt_item, judge_area):
        '''将一个kwt对象转化为数组（比如Polygon）'''
        if judge_area == True and kwt_item.area < bias:
            return []
        res = mapping(kwt_item)
        _arr = []
        # 去除重叠点的情况
        # OutputFunc.outputWarning("可能错误：",res)
        if res["coordinates"][0][0] == res["coordinates"][0][-1]:
            for point in res["coordinates"][0][0:-1]:
                _arr.append([point[0],point[1]])
        else:
            for point in res["coordinates"][0]:
                '''暂时搁置'''
                try:
                    _arr.append([point[0],point[1]])
                except BaseException:
                    pass
        return _arr

    @staticmethod
    def getPolyEdges(poly):
        edges = []
        for index in range(len(poly)):
            if index < len(poly)-1:
                edges.append([poly[index],poly[index+1]])
            else:
                if poly[index] != poly[0]:
                    edges.append([poly[index],poly[0]])
        return edges

    @staticmethod
    def getInnerFitRectangle(poly, x, y):
        left_pt, bottom_pt, right_pt, top_pt = GeometryAssistant.getBoundPoint(poly) # 获得全部边界点
        intial_pt = [top_pt[0] - left_pt[0], top_pt[1] - bottom_pt[1]] # 计算IFR初始的位置
        ifr_width = x - right_pt[0] + left_pt[0]  # 获得IFR的宽度
        ifr = [[intial_pt[0], intial_pt[1]], [intial_pt[0] + ifr_width, intial_pt[1]], [intial_pt[0] + ifr_width, y], [intial_pt[0], y]]
        return ifr
    
    @staticmethod
    def getIFRWithBounds(poly,x,y):
        left_pt, bottom_pt, right_pt, top_pt = GeometryAssistant.getBoundPoint(poly) # 获得全部边界点
        intial_pt = [top_pt[0] - left_pt[0], top_pt[1] - bottom_pt[1]] # 计算IFR初始的位置
        ifr_width = x - right_pt[0] + left_pt[0]  # 获得IFR的宽度
        ifr = [[intial_pt[0], intial_pt[1]], [intial_pt[0] + ifr_width, intial_pt[1]], [intial_pt[0] + ifr_width, y], [intial_pt[0], y]]
        return ifr, [intial_pt[0],intial_pt[1],intial_pt[0]+ifr_width,y]
    
    @staticmethod
    def getSlide(poly,x,y):
        '''获得平移后的情况'''
        new_vertex=[]
        for point in poly:
            new_point = [point[0]+x,point[1]+y]
            new_vertex.append(new_point)
        return new_vertex

    @staticmethod
    def normData(poly,num):
        for ver in poly:
            ver[0]=ver[0]*num
            ver[1]=ver[1]*num

    @staticmethod
    def slidePoly(poly,x,y):
        '''将对象平移'''
        for point in poly:
            point[0] = point[0] + x
            point[1] = point[1] + y
    
    @staticmethod
    def slideToPoint(poly,pt):
        '''将对象平移'''
        top_pt = GeometryAssistant.getTopPoint(poly)
        x,y = pt[0] - top_pt[0], pt[1] - top_pt[1]
        for point in poly:
            point[0] = point[0] + x
            point[1] = point[1] + y

    @staticmethod
    def getDirectionalVector(vec):
        _len=sqrt(vec[0]*vec[0]+vec[1]*vec[1])
        return [vec[0]/_len,vec[1]/_len]

    @staticmethod
    def deleteOnline(poly):
        '''删除两条直线在一个延长线情况'''
        new_poly=[]
        for i in range(-2,len(poly)-2):
            vec1 = GeometryAssistant.getDirectionalVector([poly[i+1][0]-poly[i][0],poly[i+1][1]-poly[i][1]])
            vec2 = GeometryAssistant.getDirectionalVector([poly[i+2][0]-poly[i+1][0],poly[i+2][1]-poly[i+1][1]])
            if abs(vec1[0]-vec2[0])>bias or abs(vec1[1]-vec2[1])>bias:
                new_poly.append(poly[i+1])
        return new_poly

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
            if pt[1] < min_y:
                min_y = pt[1]
                bottom_pt = [pt[0],pt[1]]
        return bottom_pt

    @staticmethod
    def getRightPoint(poly):
        right_pt,max_x = [], -999999999
        for pt in poly:
            if pt[0] > max_x:
                max_x = pt[0]
                right_pt = [pt[0],pt[1]]
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
            if pt[0] < min_x:
                min_x = pt[0]
                left_pt = [pt[0],pt[1]]
            if pt[0] > max_x:
                max_x = pt[0]
                right_pt = [pt[0],pt[1]]
            if pt[1] > max_y:
                max_y = pt[1]
                top_pt = [pt[0],pt[1]]
            if pt[1] < min_y:
                min_y = pt[1]
                bottom_pt = [pt[0],pt[1]]
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
    def judgePositive(pt1, pt2, k):
        if k%2 == 0:
            if pt1[1] > pt2[1]:
                return 1
            elif pt1[1] < pt2[1]:
                return -1
            return 0
        if k%2 == 1:
            if pt2[0] > pt1[0]:
                return 1
            elif pt2[0] < pt1[0]:
                return -1
            return 0
        return 0

    @staticmethod
    def judgeLeft(pt1, pt2):
        x,y = 0,0
        if pt2[1] - pt1[1] > 0:
            x = 1
        elif pt2[1] - pt1[1] < 0:
            x = -1
        if pt2[0] - pt1[0] > 0:
            y = 1
        elif pt2[0] - pt1[0] < 0:
            y = -1
        return x,y

    @staticmethod
    def getAdjustRange(original_border_range, first_pt, to_real):
        '''部分情况需要根据相对位置调整范围'''
        new_border_range = []
        for i in range(4):
            border_range = []
            for item in original_border_range[i]:
                if to_real == True:
                    border_range.append([item[0]+first_pt[i%2],item[1]+first_pt[i%2]])
                else:
                    border_range.append([item[0]-first_pt[i%2],item[1]-first_pt[i%2]])
            new_border_range.append(border_range)
        return new_border_range

    @staticmethod
    def getFeasiblePt(ifr_bound, infeasible_border_range):
        '''求解可行域的中的可行点，从左下角逆时针'''
        potential_points = []
        for k, every_border_range in enumerate(infeasible_border_range):
            all_position = list(set([p for bound in every_border_range for p in bound] + [ifr_bound[k%2],ifr_bound[k%2+2]]))
            for position in all_position:
                feasible = True
                for test_range in every_border_range:
                    if test_range[0] < position < test_range[1] or position > ifr_bound[k%2] or position < ifr_bound[k%2+2]:
                        feasible = False
                        break
                if feasible == True:
                    if k%2 == 0:
                        potential_points.append([position, ifr_bound[k+1]])
                    else:
                        potential_points.append([ifr_bound[3-k], position])
        return potential_points


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
    def slidePoly(poly,x,y):
        for point in poly:
            point[0]=point[0]+x
            point[1]=point[1]+y

    @staticmethod
    def boundsContain(bounds, pt):
        if pt[0] >= bounds[0] and pt[0] <= bounds[2] and pt[1] >= bounds[1] and pt[1] <= bounds[3]:
            return True
        return False
        
    @staticmethod
    def judgeContain(pt,parts):
        '''判断点是否包含在NFP凸分解后的凸多边形列表中 输入相对位置点'''
        def cross(p0,p1,p2):
            '''计算叉乘'''
            return (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])

        for part in parts: # 对凸多边形逐个判断
            n=len(part)
            if cross(part[0],pt,part[1])>bias or cross(part[0],pt,part[n-1])<-bias:
                continue
            i=1
            j=n-1
            line=-1
            while i<=j:
                mid=int((i+j)/2)
                if cross(part[0],pt,part[mid])>0:
                    line=mid
                    j=mid-1
                else:
                    i=mid+1
            if cross(part[line-1],pt,part[line])<bias:
                return True
        return False

    @staticmethod
    def getSlide(poly,x,y):
        new_vertex=[]
        for point in poly:
            new_point=[point[0]+x,point[1]+y]
            new_vertex.append(new_point)
        return new_vertex

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
    def getPolysRight(polys):
        _max=0
        for i in range(0,len(polys)):
            [x,y] = LPAssistant.getRightPoint(polys[i])
            if x > _max:
                _max=x
        return _max

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