# 参考资料 Evolution of a salesman: A complete genetic algorithm tutorial for Python
# https://towardsdatascience.com/evolution-of-a-salesman-a-complete-genetic-algorithm-tutorial-for-python-6fe5d2b3ca35
import numpy as np, random, operator, pandas as pd, matplotlib.pyplot as plt
from geo_func import geoFunc
from gravity_lowest import GravityLowestAlgorithm
import json

# 形状对象
class Poly:
    def __init__(self, index, points):
        self.points=points
        self.index=index
        self.ratation=0

# 适配程度，用于进化选择
def Fitness(sequence):
    pp=GravityLowestAlgorithm(sequence).start()
    fitness=1000/float(pp.contain_height) # 选择倒数
    return fitness

# 创建一个序列
def createSequence(polyList):
    sequence = random.sample(polyList, len(polyList))
    return sequence

# 初始化种群
def initialPopulation(popSize, polyList):
    population = []

    for i in range(0, popSize):
        population.append(createSequence(polyList)) # 生成随机序列
    return population

# 对序列进行排序
def rankSequences(population):
    fitnessResults = {}
    for i in range(0,len(population)):
        print("计算第",i+1,"个序列")
        fitnessResults[i] = Fitness(population[i]) # index和fitness共同排序
    popRanked=sorted(fitnessResults.items(), key = operator.itemgetter(1), reverse = True) # 排序，包含index
    return  popRanked

# 根据排序选择序列
def selection(popRanked, eliteSize):
    selectionResults = []
    df = pd.DataFrame(np.array(popRanked), columns=["Index","Fitness"])
    df['cum_sum'] = df.Fitness.cumsum() # 计算累加值
    df['cum_perc'] = 100*df.cum_sum/df.Fitness.sum() # 计算百分比
    
    for i in range(0, eliteSize):
        selectionResults.append(popRanked[i][0])
    for i in range(0, len(popRanked) - eliteSize):
        pick = 100*random.random()
        for i in range(0, len(popRanked)):
            if pick <= df.iat[i,3]:
                selectionResults.append(popRanked[i][0])
                break
    return selectionResults

# 获得matingPool用于繁殖
def matingPool(population, selectionResults):
    matingpool = []
    for i in range(0, len(selectionResults)):
        index = selectionResults[i]
        matingpool.append(population[index])
    return matingpool

# 序列交配
def breed(parent1, parent2):
    child = []
    childP1 = []
    childP2 = []
    
    geneA = int(random.random() * len(parent1))
    geneB = int(random.random() * len(parent1))
    
    startGene = min(geneA, geneB)
    endGene = max(geneA, geneB)

    for i in range(startGene, endGene):
        childP1.append(parent1[i])
        
    childP2 = [item for item in parent2 if item not in childP1]

    child = childP1 + childP2
    return child

# 繁殖种群，输入pool和size
def breedPopulation(matingpool, eliteSize):
    children = []
    length = len(matingpool) - eliteSize
    pool = random.sample(matingpool, len(matingpool))

    for i in range(0,eliteSize):
        children.append(matingpool[i])
    
    for i in range(0, length):
        child = breed(pool[i], pool[len(matingpool)-i-1])
        children.append(child)
    return children

# 个体突变，随机交换
def mutate(individual, mutationRate):
    for swapped in range(len(individual)):
        if(random.random() < mutationRate):
            swapWith = int(random.random() * len(individual))
            
            poly1 = individual[swapped]
            poly2 = individual[swapWith]
            
            individual[swapped] = poly1
            individual[swapWith] = poly2
    return individual

# 种群突变
def mutatePopulation(population, mutationRate):
    mutatedPop = []
    
    for ind in range(0, len(population)):
        mutatedInd = mutate(population[ind], mutationRate)
        mutatedPop.append(mutatedInd)

    return mutatedPop

# 获得下一个形状
def nextGeneration(currentGen, eliteSize, mutationRate):
    popRanked = rankSequences(currentGen) # 获得子代
    print("Fitness : ",str(popRanked[0][1]))
    selectionResults = selection(popRanked, eliteSize)
    matingpool = matingPool(currentGen, selectionResults)
    children = breedPopulation(matingpool, eliteSize)
    nextGeneration = mutatePopulation(children, mutationRate)
    return nextGeneration,popRanked

# GA算法核心步骤
def geneticAlgorithm(population, popSize, eliteSize, mutationRate, generations):
    pop = initialPopulation(popSize, population) # 生成随机序列
    popRanked=[] # 计算出的pop的排列

    # 持续获得下一代
    for i in range(0, generations):
        print("############################计算第",i+1,"代#######################################")
        pop,popRanked = nextGeneration(pop, eliteSize, mutationRate) 
    
    print("Final fitness: " + str(popRanked[0][1]))
    bestSequenceIndex = popRanked[0][0]
    bestSequence = pop[bestSequenceIndex]
    return bestSequence

'''需要修改'''
# 带打点的函数
def geneticAlgorithmPlot(population, popSize, eliteSize, mutationRate, generations):
    pop = initialPopulation(popSize, population)
    progress = []
    progress.append(1 / rankSequences(pop)[0][1]) # 存储最好的情况
    
    for i in range(0, generations):
        print("############################计算第",i,"代#######################################")
        pop,popRanked = nextGeneration(pop, eliteSize, mutationRate)
        progress.append(1 / rankSequences(pop)[0][1])
    
    plt.plot(progress)
    plt.ylabel('Height')
    plt.xlabel('Generation')
    plt.show()

def getData():
    index=0
    '''报错数据集有（空心）：han,jakobs1,jakobs2 '''
    '''形状过多暂时未处理：shapes、shirt、swim、trousers'''
    name=["ga","albano","blaz1","blaz2","dighe1","dighe2","fu","han","jakobs1","jakobs2","mao","marques","shapes","shirts","swim","trousers"]
    print("开始处理",name[index],"数据集") # ga为测试数据集
    '''暂时没有考虑宽度，全部缩放来表示'''
    scale=[100,0.25,100,100,20,20,20,10,20,20,0.5,20,50]
    print("缩放",scale[index],"倍")
    df = pd.read_csv("/Users/sean/Documents/Projects/Packing-Algorithm/euro_data/"+name[index]+".csv")
    polygons=[]
    for i in range(0,df.shape[0]):
        for j in range(0,df['num'][i]):
            poly=json.loads(df['polygon'][i])
            geoFunc.normData(poly,scale[index])
            polygons.append(poly)
    return polygons


def normData(polygons,num):
    for poly in polygons:
        for ver in poly:
            ver[0]=ver[0]*num
            ver[1]=ver[1]*num

if __name__=='__main__':
    '''
    种群的大小 popSize
    选择个数 eliteSize
    变异概率 mutationRate
    总的繁殖代数 generations
    ''' 
    polyList=getData()
    print("共",len(polyList),"个形状")
    print("一代10个序列")
    print("每代选择5个序列")
    print("变异概率10%")
    print("共3代")
    bestSequence=geneticAlgorithm(population=polyList, popSize=10, eliteSize=5, mutationRate=0.1, generations=3)
    print("最佳序列:")
    print(bestSequence)