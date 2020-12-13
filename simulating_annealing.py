import numpy as np, random, operator, pandas as pd, matplotlib.pyplot as plt
from tools.geofunc import GeoFunc
from tools.show import PltFunc
from tools.nfp import NFP
from tools.data import getData
from tools.packing import PackingUtil,NFPAssistant,PolyListProcessor,Poly
from heuristic import TOPOS,BottomLeftFill
import json
from shapely.geometry import Polygon,mapping
from shapely import affinity
import csv
import time
import multiprocessing
import datetime
import random
import copy

def packingLength(poly_list,history_index_list,history_length_list,width,**kw):
    polys=PolyListProcessor.getPolysVertices(poly_list)
    index_list=PolyListProcessor.getPolyListIndex(poly_list)
    length=0
    check_index=PolyListProcessor.getIndex(index_list,history_index_list)
    if check_index>=0:
        length=history_length_list[check_index]
    else:
        try:
            if 'NFPAssistant' in kw:
                blf=BottomLeftFill(width,polys,NFPAssistant=kw['NFPAssistant'])
                # blf.showAll()
                length=blf.contain_length
            else:
                length=BottomLeftFill(width,polys).contain_length
        except:
            print('出现Self-intersection')
            length=99999
        history_index_list.append(index_list)
        history_length_list.append(length)
    return length

class SA(object):
    '''
    Simulating Annealing + Bottom Left Fill
    Reference:....
    '''
    def __init__(self,poly_list):
        self.min_angle=360 # 允许旋转的最小角度
        self.width=1500 # 排列的宽度

        self.temp_now=200  # 起始温度 2000
        self.temp_end=1e-5 # 结束温度 1e-20
        self.dec_rate=0.7 # 降温速率 0.995
        self.loop_times=5 # 内循环次数
        
        self.cur_poly_list=poly_list # 当前的序列
        self.new_poly_list=poly_list # 生成新的序列

        self.history_index_list=[] # 运行过的index序列
        self.history_length_list=[] # 运行结果
        
        self.NFPAssistant=NFPAssistant(PolyListProcessor.getPolysVertices(poly_list),get_all_nfp=True)

        self.run()
    
    def newPolyList(self):
        choose_id = int(random.random() * len(self.new_poly_list))
        '''进行交换和旋转的操作，暂时不允许旋转'''
        if random.random()<=1:
            self.new_poly_list=PolyListProcessor.randomSwap(self.cur_poly_list,choose_id)
        else:
            self.new_poly_list=PolyListProcessor.randomRotate(self.cur_poly_list,self.min_angle,choose_id)
  
    def run(self):
        initial_length=packingLength(self.cur_poly_list,self.history_index_list,self.history_length_list,self.width)

        global_lowest_length_list = [] # 记录每个温度下最最低高度，理论上会下降
        temp_lowest_length_list= [] # 每个温度下的平衡高度

        global_best_list = copy.deepcopy(self.cur_poly_list) # 用于记录历史上最好蓄力
        global_lowest_length=initial_length # 全局最低高度
        
        temp_best_list=copy.deepcopy(self.cur_poly_list) # 局部温度下的最低
        temp_lowest_length=initial_length # 局部温度下的最低

        unchange_times=0

        # 开始循环寻找
        while self.temp_now>self.temp_end:
            print("当前温度：",self.temp_now)
            old_lowest_length=global_lowest_length # 统计未更改次数

            cur_length=packingLength(self.cur_poly_list,self.history_index_list,self.history_length_list,self.width,NFPAssistant=self.NFPAssistant)

            # 在某个温度下进行一定次数的寻找 
            for i in range(self.loop_times): 
                self.newPolyList()

                new_length=packingLength(self.new_poly_list,self.history_index_list,self.history_length_list,self.width,NFPAssistant=self.NFPAssistant)
                delta_length = new_length-cur_length

                if delta_length < 0: # 当前温度下如果高度更低则接受
                    temp_best_list = self.cur_poly_list = copy.deepcopy(self.new_poly_list) 
                    temp_lowest_length=new_length # 修改为新的高度
                    cur_length=new_length

                    if new_length<global_lowest_length: # 如果新的高度小于最低的高度则修改最低高度
                        global_lowest_length=new_length
                        global_best_list=copy.deepcopy(self.new_poly_list)

                elif np.random.random() < np.exp(-delta_length / self.temp_now): # 按照一定概率修改，并作为下一次检索基础
                    self.poly_list=copy.deepcopy(self.new_poly_list)
                    cur_length=new_length
                else:
                    pass # 否则不进行修改
            
            print("当前温度最低长度:",temp_lowest_length)
            print("最低长度:",global_lowest_length)

            if old_lowest_length==global_lowest_length:
                unchange_times+=1
                if unchange_times>15:
                    break
            else:
                unchange_times=0

            self.cur_poly_list=copy.deepcopy(temp_best_list) # 某温度下检索结束后取该温度下最优值
            self.temp_now*=self.dec_rate #退火
            global_lowest_length_list.append(global_lowest_length) # 全局的在每个温度下的最低高度，理论上一直在降低
            temp_lowest_length_list.append(temp_lowest_length) # 每个温度下的最低高度
            
        # print('结束温度的局部最优的序列:',temp_best_list)
        print('结束温度的局部最优高度:',temp_lowest_length)
        # print('最好序列:',global_best_list)
        print('最好序列高度:',global_lowest_length)

        PolyListProcessor.showPolyList(self.width,global_best_list)

        self.showBestResult(temp_lowest_length_list,global_lowest_length_list)
    
    def showBestResult(self,list1,list2):
        plt.figure(1)
        plt.subplot(311)
        plt.plot(list1)#每个温度下平衡路径长度
        plt.subplot(312)
        plt.plot(list2)#每个温度下最好路径长度
        plt.grid()
        plt.show() 

if __name__=='__main__':
    starttime = datetime.datetime.now()

    polys = getData(6)
    all_rotation = [0] # 禁止旋转
    poly_list = PolyListProcessor.getPolyObjectList(polys, all_rotation)

    SA(poly_list)

    endtime = datetime.datetime.now()
    print (endtime - starttime)
