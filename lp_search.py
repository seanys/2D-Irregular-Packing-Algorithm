"""
该版本开始优化性能，尽量全部采用直接几何计算
-----------------------------------
Created on Wed June 10, 2020
@author: seanys,prinway
-----------------------------------
"""
from tools.polygon import PltFunc
from tools.geo_assistant import GeometryAssistant, OutputFunc
from shapely.geometry import Polygon,Point,mapping,LineString
import pandas as pd
import numpy as np
from copy import deepcopy
from random import randint
import time
import csv # 写csv
import json
import operator
import cProfile

compute_bias = 0.000001
pd_range = 5

grid_precision = 10
# digital_precision = 0.001
digital_precision = 1

zfill_num = 5

# fu 2 shapes2_Clus 39 jakobs2_clus 70 
# jakobs1_clus 86 dighe1 103  dagli 102
# trouser 67 65  Swim_clus 89

class LPSearch(object):
    def __init__(self, **kw):
        self.line_index = 21
        self.max_time = 7200
        self.loadKey = False

        if "line_index" in kw:
            self.line_index = kw["line_index"]
        if "max_time" in kw:
            self.max_time = kw["max_time"]

        self.initialProblem(self.line_index) # 获得全部 
        self.ration_dec, self.ration_inc = 0.04, 0.01
        self.TEST_MODEL = False
        
        _str = "初始利用率为：" + str(self.total_area/(self.cur_length*self.width))
        OutputFunc.outputAttention(self.set_name,_str)
        # self.showPolys()

        self.recordStatus("record/lp_result/" + self.set_name + "_result_success.csv")
        self.recordStatus("record/lp_result/" + self.set_name + "_result_fail.csv")
        self.main()

    def main(self):
        '''核心算法部分'''
        self.shrinkBorder() # 平移边界并更新宽度        
        if self.TEST_MODEL == True:
            self.max_time = 60
        self.start_time = time.time()
        search_status = 0
        search_times = 0

        while time.time() - self.start_time < self.max_time:
            self.updateAllPairPD() # 更新当前所有重叠
            feasible = self.minimizeOverlap() # 开始最小化重叠
            if feasible == True or search_times == 5:
                # PltFunc.showPolys(self.polys,saving=True)
                search_status = 0
                _str = "当前利用率为：" + str(self.total_area/(self.cur_length*self.width))
                OutputFunc.outputInfo(self.set_name,_str)
                self.best_orientation = deepcopy(self.orientation) # 更新方向
                self.best_polys = deepcopy(self.polys) # 更新形状
                self.best_length = self.cur_length # 更新最佳高度
                with open("record/lp_result/" + self.set_name + "_result_success.csv","a+") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerows([[time.asctime( time.localtime(time.time()) ),self.line_index,search_times, feasible,self.best_length,self.total_area/(self.best_length*self.width),self.orientation,self.polys]])
                # self.showPolys()
                self.shrinkBorder() # 收缩边界并平移形状到内部来
                search_times = 0
            else:
                # self.showPolys()
                search_times = search_times + 1
                OutputFunc.outputWarning(self.set_name, "结果不可行，重新进行检索")
                with open("record/lp_result/" + self.set_name + "_result_fail.csv","a+") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerows([[time.asctime( time.localtime(time.time()) ),self.line_index,feasible,self.cur_length,self.total_area/(self.cur_length*self.width),self.orientation,self.polys]])        
                # self.extendBorder() # 扩大边界并进行下一次检索
                if search_status == 1:
                    self.shrinkBorder()
                    search_status = 0
                else:
                    self.extendBorder() # 扩大边界并进行下一次检索
                    search_status = 1    
            if self.total_area/(self.best_length*self.width) > 0.995:
                break
            if (self.set_name == "jakobs1_clus" or self.set_name == "jakobs1") and feasible == True and self.total_area/(self.best_length*self.width) > 0.8905 \
                or (self.set_name == "jakobs2_clus" or self.set_name == "jakobs2") and feasible == True and self.total_area/(self.best_length*self.width) > 0.877 \
                    or (self.set_name == "shapes0_clus" or self.set_name == "shapes0") and feasible == True and self.total_area/(self.best_length*self.width) > 0.687 \
                        or (self.set_name == "shapes1_clus" or self.set_name == "shapes1") and feasible == True and self.total_area/(self.best_length*self.width) > 0.767\
                            or (self.set_name == "shirts" and feasible == True and self.total_area/(self.best_length*self.width)) > 0.8895\
                                or (self.set_name == "marques" and feasible == True and self.total_area/(self.best_length*self.width)) > 0.9145\
                                    or (self.set_name == "fu" and feasible == True and self.total_area/(self.best_length*self.width)) > 0.924:
                        break
                


    def minimizeOverlap(self):
        '''最小化某个重叠情况'''
        self.miu = [[1]*self.polys_num for _ in range(self.polys_num)] # 计算重叠权重调整（每次都会更新）
        N,it = 50,0 # 记录计算次数
        Fitness = 9999999999999 # 记录Fitness即全部的PD
        if self.TEST_MODEL == True: # 测试模式
            N = 10
        unchange_times,last_pd = 0,0
        while it < N:
            print("第",it,"轮")
            permutation = np.arange(self.polys_num)
            np.random.shuffle(permutation)
            # permutation = [k for k in range(self.polys_num)]
            for choose_index in permutation:
                top_pt = GeometryAssistant.getTopPoint(self.polys[choose_index]) # 获得最高位置，用于计算PD
                cur_pd = self.getIndexPD(choose_index,top_pt,self.orientation[choose_index]) # 计算某个形状全部pd
                if cur_pd < self.bias: # 如果没有重叠就直接退出
                    continue
                final_pt = [top_pt[0],top_pt[1]]
                final_ori = self.orientation[choose_index] # 记录最佳情况                
                final_pd, final_pd_record = cur_pd, [0 for _ in range(self.polys_num)]
                for ori in self.allowed_rotation: # 测试全部的方向
                    if ori == 2 and self.vertical_symmetrical[self.polys_type[choose_index]] == 1:
                        continue
                    if ori == 3 and self.horizon_symmetrical[self.polys_type[choose_index]] == 1:
                        continue
                    min_pd,best_pt,best_pd_record = self.lpSearch(choose_index,ori) # 为某个形状寻找最优的位置
                    if min_pd < final_pd:
                        final_pt = [best_pt[0],best_pt[1]]
                        final_ori = ori # 更新位置和方向
                        final_pd,final_pd_record = min_pd, deepcopy(best_pd_record) # 记录最终的PD和对应的PD值
                    if min_pd == 0:
                        break
                if final_pd < cur_pd: # 更新最佳情况
                    # print(choose_index,"寻找到更优位置:", final_pt, cur_pd,"->",final_pd)
                    self.polys[choose_index] = self.getPolygon(choose_index,final_ori)
                    GeometryAssistant.slideToPoint(self.polys[choose_index],final_pt) # 平移到目标区域
                    self.orientation[choose_index] = final_ori # 更新方向
                    self.updatePD(choose_index, final_pd_record) # 更新对应元素的PD，线性时间复杂度
                    # self.showPolys(coloring = choose_index)
                    # with open("record/test.csv","a+") as csvfile:
                    #     writer = csv.writer(csvfile)
                    #     writer.writerows([[]])
                    #     writer.writerows([[self.line_index, final_pd, choose_index, self.orientation, self.polys]])        
                else:
                    # print(choose_index,"未寻找到更优位置")
                    pass
            # if self.TEST_MODEL == True: # 测试模式
            #     return
            # self.showPolys()
            total_pd, max_pair_pd = self.getPDStatus() # 获得当前的PD情况
            if total_pd < self.max_overlap:
                OutputFunc.outputWarning(self.set_name,"结果可行")                
                return True
            elif total_pd < Fitness:
                Fitness = total_pd
                it = 0
                _str = "更新最少重叠:" + str(total_pd)
                OutputFunc.outputAttention(self.set_name, _str)

            self.updateMiu(max_pair_pd) # 更新参数
            it = it + 1 # 更新计数次数

            # _str = "当前全部重叠:" + str(total_pd)
            # OutputFunc.outputInfo(self.set_name,_str) # 输出当前重叠情况

        return False

    def lpSearch(self, i, oi):
        '''Step 1 初始化全部数据'''
        polygon = self.getPolygon(i, oi) # 获得对应的形状
        ifr, ifr_bounds = GeometryAssistant.getIFRWithBounds(polygon, self.cur_length, self.width)
        ifr_edges  = GeometryAssistant.getPolyEdges(ifr) # 全部的IFR和可行的IFR
        cur_nfps, cur_nfps_bounds = self.getCurNFPs(i, oi) # 获得全部NFP及其边界

        '''Step 2 求解NFP与IFR以及其之间的交点'''
        nfp_ifr_inters = self.getNFPCutTargets(i, oi, cur_nfps, cur_nfps_bounds, ifr_bounds, ifr_edges, ifr)        
        all_nfp_inters, nfp_neighbor = self.getAllNFPInter(i, oi, cur_nfps, cur_nfps_bounds, ifr_bounds)
        all_search_targets = self.processSearchTargets(all_nfp_inters + nfp_ifr_inters, nfp_neighbor)
        all_search_targets += [[pt[0],pt[1],[],[j for j in range(self.polys_num)]] for pt in ifr]

        '''Step 3 求解最佳位置'''
        min_pd, best_pt, best_pd_record = 99999999999, [], [0 for _ in range(self.polys_num)]
        for k, search_target in enumerate(all_search_targets):
            pt = [search_target[0],search_target[1]]
            if GeometryAssistant.boundsContain(ifr_bounds, pt) == False:
                continue
            total_pd, pd_record = 0, [0 for _ in range(self.polys_num)]
            test_range = [w for w in range(self.polys_num) if w not in search_target[2]]
            for j in search_target[3]:
            # for j in test_range:
                if GeometryAssistant.boundsContain(cur_nfps_bounds[j], pt) == False:
                    continue
                pd = self.getPolyPtPD(pt, cur_nfps[j], i, oi, j, self.orientation[j])
                total_pd, pd_record[j] = total_pd + pd * self.miu[i][j], pd
            
            '''调试错误代码'''
            # total_pd_test, pd_record_test = 0, [0 for _ in range(self.polys_num)]
            # test_range = [w for w in range(self.polys_num) if w not in search_target[2]]
            # for j in test_range:
            #     if GeometryAssistant.boundsContain(cur_nfps_bounds[j], pt) == False:
            #         continue
            #     pd = self.getPolyPtPD(pt, cur_nfps[j], i, oi, j, self.orientation[j])
            #     total_pd_test, pd_record_test[j] = total_pd_test + pd * self.miu[i][j], pd

            # if abs(total_pd_test - total_pd) > 4:
            #     print(total_pd,total_pd_test)
            #     print("test_pd_record:",pd_record_test)
            #     print("pd_record:",pd_record)
            #     for w,po in enumerate(cur_nfps):
            #         print(w, po)
            #     print("!!!")

            if total_pd < min_pd:
                min_pd, best_pd_record, best_pt = total_pd, deepcopy(pd_record), [pt[0],pt[1]]
                if total_pd < self.bias:
                    break

        return min_pd, best_pt, best_pd_record

    def getNFPCutTargets(self, i, oi, cur_nfps, cur_nfps_bounds, ifr_bounds, ifr_edges, ifr):
        '''获得全部的NFP以及其切除后的结果'''
        nfp_ifr_inters = []  # 范围是从左底部点逆时针的
        for j,nfp in enumerate(cur_nfps):
            if j == i:
                continue
            bounds = cur_nfps_bounds[j]
            contain_x, contain_y = (bounds[0] > ifr_bounds[0] and bounds[2] < ifr_bounds[2]), (bounds[1] > ifr_bounds[1] and bounds[3] < ifr_bounds[3])
            # hori_key, vert_key = str(int(nfp[0][1]/digital_precision)*digital_precision).zfill(zfill_num), str(int(nfp[0][0]/digital_precision)*digital_precision).zfill(zfill_num)
            # total_key = hori_key + vert_key
            # 完全包含的情况
            if contain_x == True and contain_y == True:
                nfp_ifr_inters += [[pt[0],pt[1],[j]] for pt in nfp]
                continue
            '''考虑到NFP与IFR交点计算速度较快，暂时不考虑历史计算'''
            # 仅包含在x bounds的情况/仅包含在y bounds的情况/求解范围
            # if contain_x == True and hori_key in self.last_nfp_ifr_hori[i][oi][j][self.orientation[j]]:
            #     history_record = self.last_nfp_ifr_hori[i][oi][j][self.orientation[j]][hori_key] # 相对范围
            #     border_pts = GeometryAssistant.getAdjustPts(history_record["adjust_border_pts"], nfp[0], True)
            # elif contain_y == True and vert_key in self.last_nfp_ifr_vert[i][oi][j][self.orientation[j]]:
            #     history_record = self.last_nfp_ifr_vert[i][oi][j][self.orientation[j]][vert_key] # 相对范围
            #     border_pts = GeometryAssistant.getAdjustPts(history_record["adjust_border_pts"], nfp[0], True)
            # elif total_key in self.last_nfp_ifr[i][oi][j][self.orientation[j]]:
            #     history_record = self.last_nfp_ifr[i][oi][j][self.orientation[j]][total_key]
            #     border_pts = history_record["border_pts"]
            # else:
            '''直接计算交点的方式'''
            all_pts, inside_indexs, border_pts = GeometryAssistant.interNFPIFR(nfp, ifr_bounds, ifr_edges, ifr)
            nfp_ifr_inters += [[pt[0],pt[1],[j]] for pt in all_pts] # 增加新的目标点

            # if contain_x == True:
            #     GeometryAssistant.addRelativeRecord(self.last_nfp_ifr_hori[i][oi][j][self.orientation[j]], hori_key, inside_indexs, border_pts, nfp[0])
            # elif contain_y == True:
            #     GeometryAssistant.addRelativeRecord(self.last_nfp_ifr_vert[i][oi][j][self.orientation[j]], vert_key, inside_indexs, border_pts, nfp[0])
            # else:
            #     GeometryAssistant.addAbsoluteRecord(self.last_nfp_ifr[i][oi][j][self.orientation[j]], total_key, inside_indexs, border_pts)
            # continue
            # 记录求解结果（有历史的情况下）
            # nfp_ifr_inters += [[nfp[k][0],nfp[k][1],[j]] for k in history_record["inside_indexs"]]
            # nfp_ifr_inters += [[pt[0],pt[1],[j]] for pt in border_pts]
                    
        return nfp_ifr_inters
    
    def getAllNFPInter(self, index, ori, cur_nfps, cur_nfps_bounds, ifr_bounds):
        '''根据NFP的情况求解交点'''
        nfp_neighbor = [[w] for w in range(len(cur_nfps))] # 全部的点及其对应区域，NFP的邻接多边形
        all_nfp_inters = [] # [[pt[0],pt[1],[contain_nfp]],[]]
        for i in range(len(cur_nfps)-1):
            for j in range(i+1, len(cur_nfps)):
                if i == index or j == index:
                    continue
                bounds_i, bounds_j = cur_nfps_bounds[i], cur_nfps_bounds[j] # 获得边界
                if bounds_i[2] <= bounds_j[0] or bounds_i[0] >= bounds_j[2] or bounds_i[3] <= bounds_j[1] or bounds_i[1] >= bounds_j[3]:
                    continue
                # PltFunc.addPolygon(cur_nfps[i])
                # PltFunc.addPolygonColor(cur_nfps[j])
                # PltFunc.showPlt(width=2500,height=2500)
                '''如果外接矩形包含视为邻接（顶点后续会加进去的）'''
                if (bounds_i[0] >= bounds_j[0] and bounds_i[2] <= bounds_j[2] and bounds_i[1] >= bounds_j[1] and bounds_i[3] <= bounds_j[3]) or (bounds_j[0] >= bounds_i[0] and bounds_j[2] <= bounds_i[2] and bounds_j[1] >= bounds_i[1] and bounds_j[3] <= bounds_i[3]):
                    nfp_neighbor[i].append(j)    
                    nfp_neighbor[j].append(i)
                else:
                    inter_points, intersects = self.interBetweenNFPs(index, ori, i, self.orientation[i], j, self.orientation[j], cur_nfps, ifr_bounds, bounds_i, bounds_j) # 计算NFP之间的交点
                    if intersects == True:
                        nfp_neighbor[i].append(j) # 记录邻接情况    
                        nfp_neighbor[j].append(i) # 记录邻接情况
                    else:
                        continue
                    for pt in inter_points:
                        all_nfp_inters.append([pt[0],pt[1],[i,j]]) # 计算直接取0

        return all_nfp_inters, nfp_neighbor
    
    def processSearchTargets(self, all_original_inters, nfp_neighbor):
        '''删除重复目标并增加邻接，求解最终的邻接部分'''
        all_nfp_inters = sorted(all_original_inters, key = operator.itemgetter(0, 1))
        new_all_search_targets = [] 

        # 删除检索位置冗余
        for k,target in enumerate(all_nfp_inters):
            if abs(target[0] - all_nfp_inters[k-1][0]) < compute_bias and abs(target[1] - all_nfp_inters[k-1][1]) < compute_bias:
                new_all_search_targets[-1][2] = list(set(new_all_search_targets[-1][2] + target[2]))
                continue
            new_all_search_targets.append([target[0],target[1],target[2]])

        # 增加邻域部分
        for i,search_target in enumerate(new_all_search_targets):
            neighbor = nfp_neighbor[search_target[2][0]]
            for possible_orignal in search_target[2][0:]:
                neighbor = [k for k in neighbor if k in nfp_neighbor[possible_orignal]]
            simple_neighbor = [k for k in neighbor if k not in search_target[2]]
            new_all_search_targets[i].append(simple_neighbor)
        return new_all_search_targets

    def interBetweenNFPs(self, i, oi, m, om, n, on, cur_nfps, ifr_bounds, bounds1, bounds2):
        '''求解NFP之间的交集'''
        relative_position, target_key = self.getAdjustPt([cur_nfps[n][0][0] - cur_nfps[m][0][0],cur_nfps[n][0][1] - cur_nfps[m][0][1]], digital_precision)
        if target_key in self.last_nfp_inters[i][oi][m][om][n][on]:
            # print("历史的NFP获取")
            [relative_inter_points, intersects] = self.last_nfp_inters[i][oi][m][om][n][on][target_key]
            inter_points = GeometryAssistant.getAdjustPts(relative_inter_points, cur_nfps[m][0], True)
            feasible_inter_points = GeometryAssistant.getPointsContained(inter_points,ifr_bounds)
            return feasible_inter_points, intersects

        # print("直接计算")
        nfp1_edges, nfp2_edges = GeometryAssistant.getPolyEdges(cur_nfps[m]), GeometryAssistant.getPolyEdges(cur_nfps[n])
        inter_points, intersects = GeometryAssistant.interBetweenNFPs(nfp1_edges, nfp2_edges, bounds1, bounds2)
        relative_inter_points = GeometryAssistant.getAdjustPts(inter_points, cur_nfps[m][0], False)
        self.last_nfp_inters[i][oi][m][om][n][on][target_key] = [relative_inter_points, intersects] 
        feasible_inter_points = GeometryAssistant.getPointsContained(inter_points,ifr_bounds)

        return feasible_inter_points, intersects

    def updatePD(self, choose_index, final_pd_record):
        '''平移某个元素后更新对应的PD'''
        for i in range(self.polys_num):
            self.pair_pd_record[i][choose_index], self.pair_pd_record[choose_index][i] = final_pd_record[i], final_pd_record[i]

    def getPDStatus(self):
        '''获得当前的最佳情况'''
        total_pd,max_pair_pd = 0,0
        for i in range(self.polys_num-1):
            for j in range(i+1,self.polys_num):
                total_pd = total_pd + self.pair_pd_record[i][j]
                if self.pair_pd_record[i][j] > max_pair_pd:
                    max_pair_pd = self.pair_pd_record[i][j]
        return total_pd,max_pair_pd

    def updateAllPairPD(self):
        '''获得当前全部形状间的PD，无需调整'''
        self.pair_pd_record = [[0]*self.polys_num for _ in range(self.polys_num)] # 两两之间的pd和总的pd
        for i in range(self.polys_num - 1):
            for j in range(i+1, self.polys_num):
                top_pt, pd = GeometryAssistant.getTopPoint(self.polys[i]), 0
                nfp = self.getNFP(i, j, self.orientation[i], self.orientation[j])
                bounds = self.getBoundsbyRow(i, j, self.orientation[i], self.orientation[j], nfp[0])
                if GeometryAssistant.boundsContain(bounds,top_pt) == False:
                    continue
                pd = self.getPolyPtPD(top_pt, nfp, i, self.orientation[i], j, self.orientation[j])
                self.pair_pd_record[i][j], self.pair_pd_record[j][i] = pd, pd # 更新对应的pd

    def getPolyPtPD(self, pt, nfp, i, oi, j, oj):
        '''Step 1 首先处理参考点和全部（已经判断了是否包含Bounds）'''
        relative_pt = [pt[0] - nfp[0][0], pt[1] - nfp[0][1]]
        grid_pt, grid_key = self.newGetAdjustPt(relative_pt, grid_precision,5)
        digital_pt, digital_key = self.newGetAdjustPt(relative_pt, digital_precision,6)
        row = self.computeRow(i, j, oi, oj)
        i,j=j,i
        oi,oj=oj,oi
        i=self.polys_type[i]
        j=self.polys_type[j]
        original_grid_pt, original_digital_pt = [grid_pt[0]+nfp[0][0], grid_pt[1]+nfp[0][1]], [digital_pt[0]+nfp[0][0], digital_pt[1]+nfp[0][1]]

        '''Step 2 判断是否存在于last_grid_pds和last_digital_pds'''
        if grid_key in self.last_grid_pds[i][oi][j][oj]:
            possible_pd = self.last_grid_pds[i][oi][j][oj][grid_key]
            if possible_pd < -0.9:
                return 0
            if possible_pd >= 7.5: # 如果比较大则直接取该值
                return possible_pd
            if digital_key in self.last_digital_pds[i][oi][j][oj]: # 如果存在具体的位置
                return self.last_digital_pds[i][oi][j][oj][digital_key]
            
        '''Step 3 判断是否在外部和内外部情况'''
        if digital_key in self.last_exterior_pts[i][oi][j][oj]:
            return 0

        nfp_parts = self.nfp_parts[row]
        '''暂时删除该段'''
        if len(nfp_parts) > 0:
            if not GeometryAssistant.judgeContain(relative_pt,nfp_parts):
                self.last_exterior_pts[i][oi][j][oj][digital_key] = 1
                return 0
        else:
            if not Polygon(nfp).contains(Point(pt)):
                self.last_exterior_pts[i][oi][j][oj][digital_key] = 1
                return 0
    
        '''Step 4 求解PD结果（存在冗余计算）'''
        convex_status = self.nfps_convex_status[row]
        grid_pd = GeometryAssistant.getPtNFPPD(original_grid_pt, convex_status, nfp, self.bias)
        self.last_grid_pds[i][oi][j][oj][grid_key] = grid_pd
        if grid_pd < 7.5:
            if digital_pt[0] == grid_pt[0] and digital_pt[1] == grid_pt[1]:
                digital_pd = grid_pd
            else:
                digital_pd = GeometryAssistant.getPtNFPPD(original_digital_pt, convex_status, nfp, self.bias)
            self.last_digital_pds[i][oi][j][oj][digital_key] = digital_pd
            return digital_pd

        return grid_pd
        
    def getIndexPD(self,i,top_pt,oi):
        '''获得某个形状的全部PD，是调整后的结果'''
        total_pd = 0 # 获得全部的NFP基础
        for j in range(self.polys_num):
            total_pd = total_pd + self.pair_pd_record[i][j]*self.miu[i][j] # 计算PD，比较简单
        return total_pd

    def getAdjustPt(self, pt, precision):
        '''按照精度四舍五入'''
        new_pt = [round(pt[0]/precision)*precision, round(pt[1]/precision)*precision]
        target_key = str(int(new_pt[0])).zfill(8) + str(int(new_pt[1])).zfill(5)
        return new_pt, target_key

    def newGetAdjustPt(self, pt, precision, zfill_num):
        '''按照精度四舍五入'''
        new_pt = [round(pt[0]/precision)*precision, round(pt[1]/precision)*precision]
        target_key = str(int(new_pt[0]/precision)).zfill(zfill_num) + str(int(new_pt[1]/precision)).zfill(zfill_num)
        return new_pt, target_key
    
    def initialRecord(self):
        '''记录全部的'''
        self.last_grid_pds = [[[[{} for oj in range(len(self.allowed_rotation))] for j in range(max(self.polys_type)+1)] for oi in range(len(self.allowed_rotation))] for i in range(max(self.polys_type)+1)]
        self.last_digital_pds = [[[[{} for oj in range(len(self.allowed_rotation))] for j in range(max(self.polys_type)+1)] for oi in range(len(self.allowed_rotation))] for i in range(max(self.polys_type)+1)]
        self.last_exterior_pts = [[[[{} for oj in range(len(self.allowed_rotation))] for j in range(max(self.polys_type)+1)] for oi in range(len(self.allowed_rotation))] for i in range(max(self.polys_type)+1)]
        
        self.last_nfp_ifr = [[[[{} for oj in range(len(self.allowed_rotation))] for j in range(self.polys_num)] for oi in range(len(self.allowed_rotation))] for i in range(self.polys_num)]
        self.last_nfp_ifr_hori = [[[[{} for oj in range(len(self.allowed_rotation))] for j in range(self.polys_num)] for oi in range(len(self.allowed_rotation))] for i in range(self.polys_num)]
        self.last_nfp_ifr_vert = [[[[{} for oj in range(len(self.allowed_rotation))] for j in range(self.polys_num)] for oi in range(len(self.allowed_rotation))] for i in range(self.polys_num)]

        self.last_nfp_inters = [[[[[[{} for on in range(len(self.allowed_rotation))] for n in range(self.polys_num)] for om in range(len(self.allowed_rotation))] for m in range(self.polys_num)] for oi in range(len(self.allowed_rotation))] for i in range(self.polys_num)]
        # 加载key
        if self.loadKey:
            all_keys = pd.read_csv("data/new/" + self.set_name + "_key.csv")
            for row in range(all_keys.shape[0]):
                i=all_keys["i"][row]
                oi=all_keys["oi"][row]
                j=all_keys["j"][row]
                oj=all_keys["oj"][row]
                grid_dict=json.loads(all_keys["grid"][row])
                digital_dict=json.loads(all_keys["digital"][row])
                exterior_dict=json.loads(all_keys["exterior"][row])
                for key in grid_dict.keys():
                    self.last_grid_pds[i][oi][j][oj][key]=grid_dict[key]
                for key in digital_dict.keys():
                    self.last_digital_pds[i][oi][j][oj][key]=digital_dict[key]
                for key in exterior_dict.keys():
                    self.last_exterior_pts[i][oi][j][oj][key]=exterior_dict[key]

    def getNFP(self, i, j, oi, oj):
        '''根据形状和角度获得NFP的情况'''
        row = self.computeRow(i, j, oi, oj)
        bottom_pt = GeometryAssistant.getBottomPoint(self.polys[j])
        nfp = GeometryAssistant.getSlide(self.all_nfps[row], bottom_pt[0], bottom_pt[1])
        return nfp
        
    def getCurNFPs(self, i, oi):
        '''获得全部的NFP和切割后的效果'''
        cur_nfps, cur_nfps_bounds = [],[]
        for j in range(self.polys_num):
            if j == i:
                cur_nfps.append([]), cur_nfps_bounds.append([0,0,0,0])
                continue
            nfp = self.getNFP(i, j, oi, self.orientation[j])
            cur_nfps.append(nfp) # 添加NFP
            cur_nfps_bounds.append(self.getBoundsbyRow(i, j, oi, self.orientation[j], nfp[0])) # 添加边界
            # if nfp == []:
            #     OutputFunc.outputWarning(("出现错误"))
                # PltFunc.showPlt()
            # PltFunc.addPolygonColor(cur_nfps[j])
            # PltFunc.addPolygon(self.polys[j])
            # PltFunc.addPolygon(self.polys[i])
            # PltFunc.addPolygonColor([[cur_nfps_bounds[j][0],cur_nfps_bounds[j][1]],[cur_nfps_bounds[j][2],cur_nfps_bounds[j][1]],[cur_nfps_bounds[j][2],cur_nfps_bounds[j][3]],[cur_nfps_bounds[j][0],cur_nfps_bounds[j][3]]])
            # PltFunc.showPlt()
        return cur_nfps, cur_nfps_bounds

    def getBoundsbyRow(self, i, j, oi, oj, first_pt):
        row = self.computeRow(i, j, oi, oj)
        bounds = self.nfps_bounds[row]
        return [bounds[0] + first_pt[0], bounds[1] + first_pt[1], bounds[2] + first_pt[0], bounds[3] + first_pt[1]]

    def computeRow(self, i, j, oi, oj):
        return self.polys_type[j]*self.types_num*len(self.allowed_rotation)*len(self.allowed_rotation) + self.polys_type[i]*len(self.allowed_rotation)*len(self.allowed_rotation) + oj*len(self.allowed_rotation) + oi # i为移动形状，j为固定位置

    def updateMiu(self,max_pair_pd):
        """寻找到更优位置之后更新"""
        for i in range(self.polys_num-1):
            for j in range(i+1,self.polys_num):
                self.miu[i][j] = self.miu[i][j] + self.pair_pd_record[i][j]/max_pair_pd
                self.miu[j][i] = self.miu[j][i] + self.pair_pd_record[j][i]/max_pair_pd

    def shrinkBorder(self):
        '''收缩边界，将超出的多边形左移'''
        # 收缩边界宽度
        self.cur_length = self.best_length*(1 - self.ration_dec)
        '''设定各种的最值限制'''
        if self.total_area/(self.cur_length*self.width) > 1:
            self.cur_length = self.total_area/self.width
        if (self.set_name == "jakobs1_clus" or self.set_name == "jakobs1") and self.total_area/(self.cur_length*self.width) > 0.8910:
            self.cur_length = self.total_area/(self.width*0.8910)
        if (self.set_name == "jakobs2_clus" or self.set_name == "jakobs2") and self.total_area/(self.cur_length*self.width) > 0.8773:
            self.cur_length = self.total_area/(self.width*0.8773)
        if (self.set_name == "shapes0_clus" or self.set_name == "shapes0") and self.total_area/(self.cur_length*self.width) > 0.6879:
            self.cur_length = self.total_area/(self.width*0.6879)
        if (self.set_name == "shapes1_clus" or self.set_name == "shapes1") and self.total_area/(self.cur_length*self.width) > 0.7673:
            self.cur_length = self.total_area/(self.width*0.7673)
        if self.set_name == "shirts" and self.total_area/(self.cur_length*self.width) > 0.8896:
            self.cur_length = self.total_area/(self.width*0.8896)
        if self.set_name == "marques" and self.total_area/(self.cur_length*self.width) > 0.9150:
            self.cur_length = self.total_area/(self.width*0.9150)
        if self.set_name == "fu" and self.total_area/(self.cur_length*self.width) > 0.9250:
            self.cur_length = self.total_area/(self.width*0.9250)
        # 把形状全部内移
        for index,poly in enumerate(self.polys):
            right_pt = GeometryAssistant.getRightPoint(poly)
            if right_pt[0] > self.cur_length:
                delta_x = self.cur_length - right_pt[0]
                GeometryAssistant.slidePoly(poly,delta_x,0)
        _str = "当前目标利用率" + str(self.total_area/(self.cur_length*self.width))
        OutputFunc.outputWarning(self.set_name,_str)

    def extendBorder(self):
        '''扩大边界'''
        self.cur_length = self.best_length*(1 + self.ration_inc)
        _str = "当前目标利用率" + str(self.total_area/(self.cur_length*self.width))

    def getPolygon(self, index, orientation):
        '''获得某个形状'''
        return deepcopy(self.all_polygons[self.polys_type[index]][orientation])

    def initialProblem(self, index):
        '''获得某个解，基于该解进行优化'''
        _input = pd.read_csv("record/lp_initial.csv")
        self.set_name = _input["set_name"][index]
        self.width = _input["width"][index]
        self.bias = _input["bias"][index]
        self.max_overlap = _input["max_overlap"][index]
        self.allowed_rotation = json.loads(_input["allowed_rotation"][index])
        self.total_area = _input["total_area"][index]
        self.polys, self.best_polys = json.loads(_input["polys"][index]), json.loads(_input["polys"][index]) # 获得形状
        self.polys_type = json.loads(_input["polys_type"][index]) # 记录全部形状的种类
        self.polys_num = len(self.polys)
        self.types_num = _input["types_num"][index] # 记录全部形状的种类
        self.orientation, self.best_orientation = json.loads(_input["orientation"][index]),json.loads(_input["orientation"][index]) # 当前的形状状态（主要是角度）
        self.total_area = _input["total_area"][index] # 用来计算利用率
        self.use_ratio = [] # 记录利用率
        self.getPreData() # 获得NFP和全部形状
        self.cur_length = GeometryAssistant.getPolysRight(self.polys) # 获得当前高度
        self.best_length = self.cur_length # 最佳高度
        self.initialRecord() # 更新全部的记录
        print("一共",self.polys_num,"个形状")

    def getPreData(self):
        '''获得全部的NFP和各个方向的形状'''
        self.all_polygons = [] # 存储所有的形状及其方向
        fu = pd.read_csv("data/" + self.set_name + "_orientation.csv") 
        # 加载全部形状
        for i in range(fu.shape[0]):
            polygons=[]
            for j in self.allowed_rotation:
                polygons.append(json.loads(fu["o_"+str(j)][i]))
            self.all_polygons.append(polygons)
        # 加载是否对称
        if len(self.allowed_rotation) >= 2:
            self.vertical_symmetrical = []
            for i in range(fu.shape[0]):
                self.vertical_symmetrical.append(fu["ver_sym"][i])
        if len(self.allowed_rotation) == 4:
            self.horizon_symmetrical = []
            for i in range(fu.shape[0]):
                self.horizon_symmetrical.append(fu["hori_sym"][i])
        # 加载NFP的属性
        self.nfps_convex_status,self.nfps_vertical_direction,self.nfps_bounds,self.all_nfps,self.nfp_parts = [],[],[],[],[]
        nfps = pd.read_csv("data/" + self.set_name + "_nfp.csv") # 获得NFP
        for i in range(nfps.shape[0]):
            self.nfps_convex_status.append(json.loads(nfps["convex_status"][i]))
            self.nfps_vertical_direction.append(json.loads(nfps["vertical_direction"][i]))
            self.nfps_bounds.append(json.loads(nfps["bounds"][i]))
            self.all_nfps.append(json.loads(nfps["nfp"][i]))
            self.nfp_parts.append(json.loads(nfps["nfp_parts"][i]))

    def showPolys(self,saving = False, coloring = None):
        '''展示全部形状以及边框'''
        for index, poly in enumerate(self.polys):
            if coloring != None and index == coloring:
                PltFunc.addPolygonColor(poly,"red") # 红色突出显示
            else:
                PltFunc.addPolygon(poly)
        PltFunc.addPolygonColor([[0,0], [self.cur_length,0], [self.cur_length,self.width], [0,self.width]])
        # PltFunc.showPlt(width=1500, height=1500)
        # PltFunc.showPlt(width=2000, height=2000)
        PltFunc.showPlt(width=2500, height=2500)

    def recordStatus(self, _path):
        with open(_path,"a+") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows([[]])
            writer.writerows([[time.asctime( time.localtime(time.time()) ), self.line_index, "开始运行[全局邻域-检验重叠] 初始利用率", self.total_area/(self.best_length*self.width)]])


if __name__=='__main__':
    LPSearch()
