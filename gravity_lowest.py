from shapely.geometry import Polygon,Point,mapping,LineString
from nfp import NFP
from data import getData
from geo_func import geoFunc

class GravityLowestAlgorithm(object):
    def __init__(self,polygons):
        self.width=2000
        self.height=15000
        self.polygons=polygons

    def start(self):
        # self.storeOrginal()
        # print(polygons)
        self.placeFirstPoly()

        for i in range(1,len(polygons)):
            print("##############################放置第",i+1,"个形状#################################")
            self.placePoly(i)
        
        self.getHeight()
        print("height:",self.contain_height)
        
        self.showAll()
        self.storeResult()

    def storeOrginal(self):
        with open("/Users/sean/Documents/Projects/Packing-Algorithm/arrangements/orginal.csv","a+") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows([[time.asctime(time.localtime(time.time())),"blaze",self.polygons]])

    def storeResult(self):
        with open("/Users/sean/Documents/Projects/Packing-Algorithm/record/record.csv","a+") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows([[time.asctime(time.localtime(time.time())),"blaze",self.contain_height,self.polygons]])

    def getHeight(self):
        _max=0
        for i in range(1,len(self.polygons)):
            top_index=geoFunc.checkTop(self.polygons[i])
            top=self.polygons[i][top_index][1]
            if top>_max:
                _max=top
        self.contain_height=_max
        pltFunc.addLine([[0,self.contain_height],[self.width,self.contain_height]],color="blue")

    def placePoly(self,index):
        '''
        放置某一个index的形状进去
        '''
        adjoin=self.polygons[index]
        ifp=self.getInnerFitRectangle(self.polygons[index])
        differ_region=Polygon(ifp)
        # 求解NFP和IFP的资料
        for main_index in range(0,index):
            main=self.polygons[main_index]
            nfp=NFP(main,adjoin).nfp
            differ_region=differ_region.difference(Polygon(nfp))

        # print(differ_region)
        differ=geoFunc.polyToArr(differ_region)

        differ_index=self.getBottomLeft(differ)
        refer_pt_index=geoFunc.checkTop(adjoin)
        geoFunc.slideToPoint(self.polygons[index],adjoin[refer_pt_index],differ[differ_index])        

    def getBottomLeft(self,poly):
        bl=[] # bottom left的全部点
        min_y=999999
        # 采用重心最低的原则
        for i,pt in enumerate(poly):
            pt_object={
                    "index":i,
                    "x":pt[0],
                    "y":pt[1]
            }
            if pt[1]<min_y:
                # 如果y更小，那就更新bl
                min_y=pt[1]
                bl=[pt_object]
            elif pt[1]==min_y:
                # 相同则添加这个点
                bl.append(pt_object)
            else:
                pass
        if len(bl)==1:
            return bl[0]["index"]
        else:
            min_x=bl[0]["x"]
            one_pt=bl[0]
            for pt_index in range(1,len(bl)):
                if bl[pt_index]["x"]<min_x:
                    one_pt=bl[pt_index]
                    min_x=one_pt["x"]
            return one_pt["index"]

    '''修改展示高度'''
    def showAll(self):
        for i in range(0,len(self.polygons)):
            pltFunc.addPolygon(self.polygons[i])
        pltFunc.showPlt(width=self.width,height=self.contain_height)
    
    def placeFirstPoly(self):
        '''
        放置第一个形状进去，并平移到left-bottom
        '''
        poly=self.polygons[0]
        poly_index=geoFunc.checkTop(poly)
        left_index,bottom_index,right_index,top_index=geoFunc.checkBound(poly)
        
        move_x=poly[left_index][0]
        move_y=poly[bottom_index][1]
        geoFunc.slidePoly(poly,0,-move_y)

    def getInnerFitRectangle(self,poly):
        '''
        获得IFR，同时平移到left-bottom
        '''
        poly_index=geoFunc.checkTop(poly)
        left_index,bottom_index,right_index,top_index=geoFunc.checkBound(poly)
        
        move_x=poly[left_index][0]
        move_y=poly[bottom_index][1]
        geoFunc.slidePoly(poly,-move_x,-move_y)

        refer_pt=[poly[poly_index][0],poly[poly_index][1]]
        width=self.width-poly[right_index][0]
        height=self.height-poly[top_index][1]

        IFR=[refer_pt,[refer_pt[0]+width,refer_pt[1]],[refer_pt[0]+width,refer_pt[1]+height],[refer_pt[0],refer_pt[1]+height]]
        
        return IFR
    
    def getInnerFitRectangleNew(self,poly):
        '''
        获得IFR，不平移
        '''
        poly_index=geoFunc.checkBottom(poly)
        left_index,bottom_index,right_index,top_index=geoFunc.checkBound(poly)
        
        move_x=poly[left_index][0]
        move_y=poly[top_index][1]
        new_poly=geoFunc.getSlide(poly,-move_x,-move_y)

        refer_pt=[new_poly[poly_index][0],new_poly[poly_index][1]]
        width=self.width-new_poly[right_index][0]
        height=self.height-new_poly[bottom_index][1]

        IFR=[refer_pt,[refer_pt[0]+width,refer_pt[1]],[refer_pt[0]+width,refer_pt[1]+height],[refer_pt[0],refer_pt[1]+height]]
        print("计算出结果:",IFR)

        return IFR
    
    # 形状收缩
    def normData(self,num):
        for poly in self.polygons:
            for ver in poly:
                ver[0]=ver[0]*num
                ver[1]=ver[1]*num

if __name__ == '__main__':
    GravityLowestAlgorithm(getData()).start()
