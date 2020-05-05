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

class GA(object):
    '''
    参考文献：A 2-exchange heuristic for nesting problems 2002
    '''
    def __init__(self,width,poly_list,nfp_asst=None,generations=10,pop_size=20):
        self.width=width
        self.minimal_rotation=360 # 最小的旋转角度
        self.poly_list=poly_list

        self.ga_multi=False # 开了多进程反而更慢
        if self.ga_multi:
            multiprocessing.set_start_method('spawn',True) 

        self.elite_size=10 # 每一代选择个数
        self.mutate_rate=0.1 # 变异概率
        self.generations=generations # 代数
        self.pop_size=pop_size # 每一代的个数

        self.history_index_list=[]
        self.history_length_list=[]
        
        if nfp_asst:
            self.NFPAssistant=nfp_asst
        else:
            self.NFPAssistant=NFPAssistant(PolyListProcessor.getPolysVertices(poly_list),get_all_nfp=True)

        self.geneticAlgorithm()

        self.plotRecord()

    # GA算法核心步骤
    def geneticAlgorithm(self):
        self.pop = [] # 种群记录
        self.length_record = [] # 记录高度
        self.lowest_length_record = [] # 记录全局高度
        self.global_best_sequence = [] # 全局最优序列
        self.global_lowest_length = 9999999999 # 全局最低高度
        
        # 初步的随机数组
        for i in range(0, self.pop_size):
            _list=copy.deepcopy(self.poly_list)
            random.shuffle(_list)
            self.pop.append(_list)

        # 持续获得下一代
        for i in range(0, self.generations):
            print("############################ Compute the ",i+1,"th generation #######################################")
            self.getLengthRanked() # 高度排列
            self.getNextGeneration() # 获得下一代

            # 高度记录与最低高度处理
            self.length_record.append(self.fitness_ranked[0][1])
            if self.fitness_ranked[0][1]<self.global_lowest_length:
                self.global_lowest_length=self.fitness_ranked[0][1]
                self.global_best_sequence=self.pop[self.fitness_ranked[0][0]]
            self.lowest_length_record.append(self.global_lowest_length)
            # print(self.global_lowest_length)

        # print("Final length: " + str(self.global_lowest_length))

        blf=BottomLeftFill(self.width,PolyListProcessor.getPolysVertices(self.global_best_sequence),NFPAssistant=self.NFPAssistant)
        blf.showAll()


    def plotRecord(self):
        plt.plot(self.lowest_length_record)
        plt.ylabel('Length')
        plt.xlabel('Generation')
        plt.show()

    # 对序列进行排序
    def getLengthRanked(self):
        length_results = []
        self.fitness_sum = 0
        
        if self.ga_multi==True:
            tasks=[[pop] for pop in self.pop]
            pool=multiprocessing.Pool()
            results=pool.starmap(self.getLength,tasks)
            for i in range(0,len(self.pop)):
                # print("length:",results[i])
                self.fitness_sum+=1000/results[i]
                length_results.append([i,results[i],1000/results[i],PolyListProcessor.getPolyListIndex(self.pop[i])])
        else:
            for i in range(0,len(self.pop)):
                length=self.getLength(self.pop[i])
                self.fitness_sum+=1000/length
                length_results.append([i,length,1000/length,PolyListProcessor.getPolyListIndex(self.pop[i])])

        self.fitness_ranked=sorted(length_results, key = operator.itemgetter(1)) # 排序，包含index

    def getLength(self,poly_list):
        length=packingLength(poly_list,self.history_index_list,self.history_length_list,self.width,NFPAssistant=self.NFPAssistant)
        return length
    
    # 根据排序选择序列
    def getNextGeneration(self):
        # mating_pool = self.rouletteWheelSelection() # 轮盘赌方法获得足够的后代并打乱，效果不佳
        mating_pool = self.eliteSelection() # 精英选择策略
        children=mating_pool
        for i in range(0, self.pop_size - self.elite_size):
            children.append(self.breed(children[random.randint(0,self.elite_size-1)], children[random.randint(0,self.elite_size-1)]))

        # 逐一进行突变处理获得新种群
        self.pop=[]
        for item in children:
            self.pop.append(self.mutate(item))
    
    # 精英选择策略
    def eliteSelection(self):
        mating_pool=[]
        for i in range(0, self.elite_size):
            mating_pool.append(self.pop[self.fitness_ranked[i][0]])
        return mating_pool
    
    # 参考：https://github.com/mangwang/PythonForFun/blob/master/rouletteWheelSelection.py
    def rouletteWheelSelection(self):
        mating_pool=[]
        for i in range(0, self.elite_size):
            rndPoint = random.uniform(0, self.fitness_sum)
            accumulator = 0.0
            for index, item in enumerate(self.fitness_ranked):
                accumulator += item[2]
                if accumulator >= rndPoint:
                    mating_pool.append(self.pop[item[0]])
        return mating_pool

    # 序列交配修改顺序（不修改方向）
    def breed(self,parent1, parent2):
        geneA,geneB = random.randint(0,len(parent1)-1), random.randint(0,len(parent1)-1)
        start_gene,end_gene = min(geneA, geneB),max(geneA, geneB)
        
        parent1_index = PolyListProcessor.getPolyListIndex(parent1)
        parent2_index = PolyListProcessor.getPolyListIndex(parent2)

        child1_index = parent1_index[start_gene:end_gene] # 截取一部分
        child2_index = [item for item in parent2_index if item not in child1_index] # 截取剩余部分

        return PolyListProcessor.getPolysByIndex(child1_index,self.poly_list) + PolyListProcessor.getPolysByIndex(child2_index,self.poly_list)

    # 个体突变，随机交换或方向改变
    def mutate(self,individual):
        for swapped in range(len(individual)):
            if(random.random() < self.mutate_rate):
                # 首先是交换位置
                if random.random()<=0.5:
                    individual=PolyListProcessor.randomSwap(individual,swapped)
                else:
                    individual=PolyListProcessor.randomRotate(individual,self.minimal_rotation,swapped)
        return individual

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

    nfp_assistant=NFPAssistant(polys, store_nfp=False, get_all_nfp=True, load_history=True)

    GA(760,poly_list,nfp_asst=nfp_assistant)

    endtime = datetime.datetime.now()
    print (endtime - starttime)
