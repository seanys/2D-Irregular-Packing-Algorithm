'''
    Guided Cuckoo Search (GCS) 
    ---
    待优化：
        如果两个多边形没有移动则无需重新计算深度
'''
import math
import random
import numpy as np
import matplotlib.pyplot as plt
from nfp import NFP
from geo_func import geoFunc
from show import pltFunc
from gravity_lowest import GravityLowestAlgorithm


class GCS(object):
    def __init__(self, polygons):
        self.polygons = polygons  # 初始解
        self.n_polys = len(self.polygons)
        self.r_dec = 0.1  # 矩形长度减少百分比
        self.r_inc = 0.1  # 矩形长度增加百分比
        self.W = 1500  # 矩形宽度（固定值）
        self.n_c = 20  # 每代布谷鸟的个数
        self.n_mo = 20  # MinimizeOverlap的最大迭代次数
        self.maxGen = 10  # max generations
        self.penalty = np.ones((self.n_polys, self.n_polys))  # penalty weight
        self.depth = np.zeros((self.n_polys, self.n_polys))  # 渗透深度
        self.percentage = 0.5  # 每次迭代时遗弃的巢的比例
        self.bestF = 999999  # 当前最优解
        print('GCS init:', self.n_polys, 'polygons')

    def GuidedCuckooSearch(self, H, N):
        '''
        H: 初始矩形高度
        N: 迭代次数限制
        '''
        self.H = H
        H_best = self.H
        n_cur = 0
        while n_cur <= N:
            original_polygons = list(self.polygons)  # 备份当前解
            it = self.MinimizeOverlap(0, 0, 0)
            if it < self.n_mo:  # 可行解
                H_best = self.H
                self.H = (1-self.r_dec)*self.H
                print('H--: ', self.H)
            else:
                # 不可行解 还原之前的解
                self.polygons = original_polygons
                self.H = (1+self.r_inc)*self.H
                print('H++: ', self.H)
            n_cur = n_cur+1
            self.showAll()
        return H_best

    def CuckooSearch(self, poly_id, ori=''):
        '''
        poly_id: 当前多边形index
        ori: 允许旋转的角度
        '''
        cuckoos = []
        poly = self.polygons[poly_id]
        GL_Algo = GravityLowestAlgorithm(None)
        R = GL_Algo.getInnerFitRectangleNew(poly)  # 为当前多边形计算inner-fit矩形
        i = 0
        while i < self.n_c:  # 产生初始种群
            c = Cuckoo(R)
            if self.censorCuckoo(c) == False:
                continue
            cuckoos.append(c)
            print(c.getXY())
            i = i+1
        bestCuckoo = cuckoos[0]
        t = 0
        while t < self.maxGen:  # 开始搜索
            c_i = random.choice(cuckoos)
            # 通过Levy飞行产生解
            newCuckooFlag = False
            while newCuckooFlag == False:
                newX, newY = self.getCuckoos_Levy(1, bestCuckoo)
                c_i.setXY(newX[0], newY[0])
                if self.censorCuckoo(c_i):
                    newCuckooFlag = True
            self.evaluate(poly_id, c_i, ori)
            c_j = random.choice(cuckoos)
            self.evaluate(poly_id, c_j, ori)
            if c_i.getF() < c_j.getF():
                c_j = c_i
                bestCuckoo = c_j
            # 丢弃一部分最坏的巢并在新位置建立新巢
            cuckoos.sort(key=lambda x: x.getF(), reverse=True)
            newX, newY = self.getCuckoos_Levy(
                int(self.percentage*len(cuckoos))+1, bestCuckoo)
            newi = 0
            for i in range(int(len(cuckoos)*self.percentage)):
                print('----- 第', str(t+1), '代 // 第', str(i+1), '只 ----')
                if newi >= len(newX):
                    break
                c_new = Cuckoo(R)
                newCuckooFlag = False
                while newCuckooFlag == False:
                    c_new.setXY(newX[newi], newY[newi])
                    if self.censorCuckoo(c_new) == False:
                        newX, newY = self.getCuckoos_Levy(
                            int(self.percentage*len(cuckoos))+1, bestCuckoo)
                        newi = 0
                    else:
                        newCuckooFlag = True
                self.evaluate(poly_id, c_new, ori)
                cuckoos[i] = c_new
                if c_new.getF()==0:
                    break
                newi = newi+1
            cuckoos.sort(key=lambda x: x.getF(), reverse=False)
            bestCuckoo = cuckoos[0]
            bestCuckoo.slidePolytoMe(poly)
            print(bestCuckoo.getF(), bestCuckoo.getXY())
            self.bestF = bestCuckoo.getF()
            for i in range(0, self.n_polys):
                pltFunc.addPolygon(self.polygons[i])
            t = t+1
            pltFunc.saveFig(str(t))
        return bestCuckoo

    def MinimizeOverlap(self, oris, v, o):
        '''
        oris: 允许旋转的角度集合
        v: 多边形位置 实际已通过self.polygons得到
        o: 旋转的角度 后期可考虑把多边形封装成类
        '''
        n_polys = self.n_polys
        it = 0
        fitness = 999999
        while it < self.n_mo:
            Q = np.random.permutation(range(n_polys))
            for i in range(n_polys):
                curPoly = self.polygons[Q[i]]
                # 记录原始位置
                top_index = geoFunc.checkTop(curPoly)
                top = list(curPoly[top_index])
                F = self.evaluate(Q[i])  # 以后考虑旋转
                print('F of',Q[i],':',F)
                v_i = self.CuckooSearch(Q[i])
                self.evaluate(Q[i], v_i)
                F_new = v_i.getF()
                print('new F of',Q[i],':',F)
                if F_new < F:
                    print('polygon', Q[i], v_i.getXY())
                else:
                    # 平移回原位置
                    geoFunc.slideToPoint(curPoly, curPoly[top_index], top)
            fitness_new = self.evaluateAll()
            if fitness_new == 0:
                return it  # 可行解
            elif fitness_new < fitness:
                fitness = fitness_new
                it = 0
            self.updatePenalty()
            it = it+1
        return it

    def getCuckoos_Levy(self, num, best):
        # Levy flights
        # num: 选取点的个数
        # Source: https://blog.csdn.net/zyqblog/article/details/80905019
        beta = 1.5
        sigma_u = (math.gamma(1 + beta) * math.sin(math.pi * beta / 2) / (
            math.gamma((1 + beta) / 2) * beta * (2 ** ((beta - 1) / 2)))) ** (1 / beta)
        sigma_v = 1
        x0, y0 = best.getXY()
        x_delta = 0
        y_delta = 0
        resX = []
        resY = []
        for i in range(num*10):
            u = np.random.normal(0, sigma_u, 1)
            v = np.random.normal(0, sigma_v, 1)
            s = u / ((abs(v)) ** (1 / beta))
            x_delta = x_delta+s[0]
            u = np.random.normal(0, sigma_u, 1)
            v = np.random.normal(0, sigma_v, 1)
            s = u / ((abs(v)) ** (1 / beta))
            y_delta = y_delta+s[0]
            resX.append(x_delta)
            resY.append(y_delta)
        # 将所得数据缩放至合适的范围
        x_zoom = self.W/(max(resX)-min(resX))
        y_zoom = self.H/(max(resY)-min(resY))
        Levy_x = []
        Levy_y = []
        for x in resX:
            Levy_x.append(x*x_zoom+x0)
        for y in resY:
            Levy_y.append(y*y_zoom+y0)
        choice = random.sample(range(num*10), num)
        choiceX = []
        choiceY = []
        for i in range(num*10):
            if i in choice:
                choiceX.append(Levy_x[i])
                choiceY.append(Levy_y[i])
        return Levy_x, Levy_y

    def evaluate(self, poly_id, cuckoo=None, ori=None):
        F = 0
        poly = self.polygons[poly_id]
        for p in range(self.n_polys):
            # 将当前多边形的Top平移到cuckoo处
            if cuckoo != None:
                cuckoo.slidePolytoMe(poly)
            if self.polygons[p] == poly:
                continue
            F = F+self.getDepth(self.polygons[p],
                                poly, 0, 0)*self.penalty[p][poly_id]
            if F > self.bestF:
                break
        print('F:', F)
        if cuckoo:
            cuckoo.setF(F)
        else:
            return F

    def evaluateAll(self):
        F = 0
        for i in range(self.n_polys):
            for j in range(i+1, self.n_polys):
                depth = self.getDepth(self.polygons[i], self.polygons[j], 0, 0)
                self.depth[i][j] = depth
                self.depth[j][i] = depth
                F = F+depth*self.penalty[i][j]
        print('all_F:', F)
        return F

    def getDepth(self, poly1, poly2, ori1, ori2):
        '''
        固定poly1 滑动poly2
        计算poly2的checkTop到NFP的距离
        '''
        # 旋转暂未考虑
        return NFP(poly1, poly2).getDepth()

    def showAll(self):
        for i in range(0, self.n_polys):
            pltFunc.addPolygon(self.polygons[i])
        pltFunc.showPlt()

    def updatePenalty(self):
        depth_max = self.depth.max()
        for i in range(self.n_polys):
            for j in range(self.n_polys):
                if i == j:
                    continue
                self.penalty[i][j] = self.penalty[i][j] + \
                    self.depth[i][j]/depth_max

    # 检查布谷鸟是否飞出边界
    def censorCuckoo(self, c):
        if c.getXY()[0] > self.W or c.getXY()[1] > self.H or c.getXY()[0] < 0 or c.getXY()[1] < 0:
            return False
        else:
            return True


class Cuckoo(object):
    def __init__(self, IFR):
        self.F = 999999
        # 在IFR中随机选取位置
        xRank = sorted(IFR, key=lambda x: x[0])
        yRank = sorted(IFR, key=lambda x: x[1])
        self.x = random.random()*(xRank[2][0]-xRank[1][0]+1)+xRank[1][0]
        self.y = random.random()*(yRank[2][1]-yRank[1][1]+1)+yRank[1][1]

    def setF(self, F):
        self.F = F

    def getF(self):
        return self.F

    def getXY(self):
        return [self.x, self.y]

    def setXY(self, x, y):
        self.x = x
        self.y = y

    def slidePolytoMe(self, poly):
        top_index = geoFunc.checkTop(poly)
        top = poly[top_index]
        geoFunc.slideToPoint(poly, top, self.getXY())


class Test():
    def getTestPolys(self):
        return [[[0.0, 21.5], [241.5, 35.5], [495.75, 0.0], [546.25, 59.5], [683.5, 54.25], [750.0, 191.75], [704.75, 225.0], [704.75, 340.0], [750.0, 373.25], [683.5, 510.75], [546.25, 505.5], [495.75, 565.0], [241.5, 529.5], [0.0, 543.5]], [[750.0, 21.5], [991.5, 35.5], [1245.75, 0.0], [1296.25, 59.5], [1433.5, 54.25], [1500.0, 191.75], [1454.75, 225.0], [1454.75, 340.0], [1500.0, 373.25], [1433.5, 510.75], [1296.25, 505.5], [1245.75, 565.0], [991.5, 529.5], [750.0, 543.5]], [[1004.25, 551.0], [1245.75, 565.0], [1500.0, 529.5], [1550.5, 589.0], [1687.75, 583.75], [1754.25, 721.25], [1709.0, 754.5], [1709.0, 869.5], [1754.25, 902.75], [1687.75, 1040.25], [1550.5, 1035.0], [1500.0, 1094.5], [1245.75, 1059.0], [1004.25, 1073.0]], [[243.62658922173387, 552.4833080929338], [485.12658922173387, 566.4833080929338], [739.3765892217339, 530.9833080929338], [789.8765892217339, 590.4833080929338], [927.1265892217339, 585.2333080929338], [993.6265892217339, 722.7333080929338], [948.3765892217339, 755.9833080929338], [948.3765892217339, 870.9833080929338], [993.6265892217339, 904.2333080929338], [927.1265892217339, 1041.7333080929338], [789.8765892217339, 1036.4833080929338], [739.3765892217339, 1095.9833080929338], [485.12658922173387, 1060.4833080929338], [243.62658922173387, 1074.4833080929338]], [[740.7271223341615, 1094.3920859109646], [1499.2271223341615, 1094.3920859109646], [1499.2271223341615, 1159.6420859109646], [740.7271223341615, 1159.6420859109646]], [[2.2737367544323206e-13, 1159.6420859109646], [758.5, 1159.6420859109646], [758.5, 1224.8920859109646], [2.2737367544323206e-13, 1224.8920859109646]], [[758.5, 1159.6420859109646], [1516.9999999999998, 1159.6420859109646], [1516.9999999999998, 1224.8920859109646], [758.5, 1224.8920859109646]], [[2.2737367544323206e-13, 1224.8920859109646], [758.5, 1224.8920859109646], [758.5, 1290.1420859109646], [2.2737367544323206e-13, 1290.1420859109646]], [[1454.25, 1231.0566231057403], [1894.5, 1187.8066231057403], [2000.0000000000002, 1350.3066231057403], [2000.0000000000002, 1440.3066231057403], [1894.5, 1602.8066231057403], [1454.25, 1559.5566231057403]], [[758.5, 1268.1420859109646], [1198.75, 1224.8920859109646], [1304.25, 1387.3920859109646], [1304.25, 1477.3920859109646], [1198.75, 1639.8920859109646], [758.5, 1596.6420859109646]], [[0.0, 1333.3920859109644], [440.25, 1290.1420859109644], [545.75, 1452.6420859109644], [545.75, 1542.6420859109644], [440.25, 1705.1420859109646], [0.0, 1661.8920859109644]], [[1210.3065533286906, 1622.0917075610853], [1650.5565533286906, 1578.8417075610853], [1756.0565533286906, 1741.3417075610853], [1756.0565533286906, 1831.3417075610853], [1650.5565533286906, 1993.8417075610857], [1210.3065533286906, 1950.5917075610855]], [[1340.8333333333333, -2.2737367544323206e-13], [1539.8333333333333, 29.749999999999773], [1738.8333333333335, -2.2737367544323206e-13], [1757.3333333333335, 31.249999999999773], [1539.8333333333333, 76.25], [1322.3333333333333, 31.249999999999773]], [[1472.9153005733572, 66.24592223814429], [1671.9153005733572, 95.99592223814429], [1870.9153005733576, 66.24592223814429], [1889.4153005733576, 97.49592223814429], [1671.9153005733572, 142.49592223814452], [1454.4153005733572, 97.49592223814429]], [[1497.157134790609, 116.3700155444925], [1696.1571347906092, 146.1200155444925], [1895.1571347906092, 116.3700155444925], [1913.6571347906092, 147.6200155444925], [1696.1571347906092, 192.62001554449273], [1478.657134790609, 147.6200155444925]], [[1515.4757107947232, 165.6085966305349], [1714.4757107947232, 195.3585966305349], [1913.4757107947232, 165.6085966305349], [1931.9757107947232, 196.8585966305349], [1714.4757107947232, 241.85859663053512], [1496.9757107947232, 196.8585966305349]], [[1599.9999999999998, 227.56790563222418], [1702.7499999999995, 243.81790563222415], [1800.0, 227.56790563222418], [1897.249999999999, 243.81790563222415], [2000.000000000001, 227.56790563222418], [1975.0, 319.5679056322244], [1800.0, 299.0679056322244], [1624.9999999999998, 319.5679056322244]], [[1499.9999999999995, 310.7821913465101], [1602.7499999999995, 327.0321913465101], [1699.9999999999995, 310.7821913465101], [1797.2499999999986, 327.0321913465101], [1900.0000000000005, 310.7821913465101], [1874.9999999999995, 402.7821913465104], [1699.9999999999995, 382.2821913465104], [1524.9999999999995, 402.7821913465104]], [[1599.9999999999995, 393.9964770607961], [1702.7499999999995, 410.24647706079605], [1799.9999999999995, 393.9964770607961], [1897.2499999999986, 410.24647706079605], [2000.0000000000005, 393.9964770607961], [1974.9999999999995, 485.9964770607964], [1799.9999999999995, 465.4964770607964], [1624.9999999999995, 485.9964770607964]], [[1509.6650261030463, 478.3429515471534], [1612.4150261030463, 494.59295154715335], [1709.6650261030463, 478.3429515471534], [1806.9150261030454, 494.59295154715335], [1909.6650261030472, 478.3429515471534], [1884.6650261030463, 570.3429515471537], [1709.6650261030463, 549.8429515471537], [1534.6650261030463, 570.3429515471537]]]

    def testDepth(self):
        polys = self.getTestPolys()
        gcs = GCS(polys)
        poly1 = [[500.0, 500.0], [602.75, 516.25], [700.0, 500.0], [797.25, 516.25], [
            900.0, 500.0], [875.0, 592.0], [700.0, 571.5], [525.0, 592.0]]
        poly2 = [[0, 0], [102.75, 16.25], [200.0, 0.0], [297.25, 16.25],
                 [400.0, 0.0], [375.0, 92.0], [200.0, 71.5], [25.0, 92.0]]
        poly3 = [[400.0, 400.0], [602.75, 516.25], [700.0, 500.0], [797.25, 516.25], [
            900.0, 500.0], [875.0, 592.0], [700.0, 571.5], [525.0, 592.0]]
        return gcs.getDepth(poly1, poly3, 0, 0)

    def testGCS(self):
        # polygons=[]
        # polygons.append(self.getTestPolys()[0])
        # polygons.append(self.getTestPolys()[1])
        polygons=self.getTestPolys()
        num = 1  # 形状收缩
        for poly in polygons:
            for ver in poly:
                ver[0] = ver[0]*num
                ver[1] = ver[1]*num
        gcs = GCS(polygons)
        geoFunc.slidePoly(polygons[0], 500, 500)
        gcs.showAll()
        gcs.GuidedCuckooSearch(1500, 10)
        gcs.showAll()

    def testLevy(self):
        gcs = GCS(None)
        c = Cuckoo([[495.75, 565.0], [745.75, 565.0], [
                   745.75, 2000.0], [495.75, 2000.0]])
        # c.setXY(594.9059139903344, 583.4635636682448)
        c.setXY(500, 500)
        xy = gcs.getCuckoos_Levy(10, c)
        plt.plot(xy[0], xy[1])
        plt.show()


Test().testGCS()
# Test().testLevy()
