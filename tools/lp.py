from pulp import *
import random
import math

def sovleLP(a,b,c,**kw):
    # 变量所有的变量
    all_var=[] 
    if '_type' in kw and kw['_type']=="compaction":
        '''Compaction约束效果'''
        for i in range(len(c)):
            if i==len(c)-1:
                all_var.append(LpVariable("z",0))
            elif i%2==1:
                all_var.append(LpVariable("y"+formatNum(i//2),0))
            elif i%2==0:
                all_var.append(LpVariable("x"+formatNum(i//2+1),0))
    elif '_type' in kw and kw['_type']=="separation":
        '''Separation约束效果'''
        # print(len(c))
        n=-1+math.sqrt(1+len(c))
        for i in range(int(n)):
            all_var.append(LpVariable("x"+formatNum(i),0))
            all_var.append(LpVariable("y"+formatNum(i),0))
        for i in range(int(n)):
            for j in range(int(n)):
                all_var.append(LpVariable("a"+formatNum(i)+"_"+formatNum(j),0))
    else:
        for i in range(len(c)):
            all_var.append(LpVariable("x"+formatNum(i),0))
    # print(all_var)

    # 初始化限制
    prob = LpProblem("Minimize",LpMinimize)   

    # 定义目标函数
    # print("目标函数：",lpSum([c[i]*all_var[i] for i in range(len(c))]))
    prob += lpSum([c[i]*all_var[i] for i in range(len(c))])

    # 定义约束函数
    # 注意: print输出的约束会根据首字母顺序调整
    for j in range(len(a)):
        # print("约束",j,":",lpSum([a[j][i]*all_var[i] for i in range(len(c))]) >= b[j])
        prob += lpSum([a[j][i]*all_var[i] for i in range(len(c))]) >= b[j]

    prob.solve()

    result=[]
    for i,v in enumerate(prob.variables()):
        result.append(v.varValue)
        # print(v.name, "=", v.varValue)
        # if i>=144:
        #     print(v.name, "=", v.varValue)
    print("目标函数最小值 = ", value(prob.objective))
    
    return result,value(prob.objective)

def problem(a,b,c):
    print("目标问题")
    print("c:",c)
    for i in range(len(a)):
        print(a[i],b[i])

def formatNum(num):
    if num < 10:
        return "0" + str(num)
    return str(num)

if __name__=='__main__':
    # a=[[10,0,20],[0,10,5],[5,5,10]]
    # b=[10,10,10]
    # c=[1,4,10]
    # 检测例题 解：0，12，5，8 目标函数：-19
    c = [1,-2,1,0]
    a = [[1,1,-2,1],[-1,-1,2,-1],[-2,1,-4,0],[1,-2,4,0]]
    b = [10,-10,-8,-4]
    sovleLP(a,b,c)
    