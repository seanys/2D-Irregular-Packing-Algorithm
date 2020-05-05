import matplotlib.pyplot as plt

class PltFunc(object):

    def addPolygon(poly):
        for i in range(0,len(poly)):
            if i == len(poly)-1:
                PltFunc.addLine([poly[i],poly[0]])
            else:
                PltFunc.addLine([poly[i],poly[i+1]])

    def addPolygonColor(poly):
        for i in range(0,len(poly)):
            if i == len(poly)-1:
                PltFunc.addLine([poly[i],poly[0]],color="blue")
            else:
                PltFunc.addLine([poly[i],poly[i+1]],color="blue")

    def addLine(line,**kw):
        if len(kw)==0:
            plt.plot([line[0][0],line[1][0]],[line[0][1],line[1][1]],color="black",linewidth=0.5)
        else:
            plt.plot([line[0][0],line[1][0]],[line[0][1],line[1][1]],color=kw["color"],linewidth=0.5)            
    
    def showPlt(**kw):
        if len(kw)>0:
            if "minus" in kw:
                plt.axhline(y=0,c="blue")
                plt.axvline(x=0,c="blue")
                plt.axis([-kw["minus"],kw["width"],-kw["minus"],kw["height"]])
                
            else:
                plt.axis([0,kw["width"],0,kw["height"]])
        else:
            plt.axis([0,1000,0,1000])
            # plt.axis([-1000,2000,-979400.4498015114,20000])
            # plt.axis([-500,1000,0,1500])
        plt.show()
        plt.clf()

    def showPolys(polys):
        for poly in polys:
            PltFunc.addPolygon(poly)
        PltFunc.showPlt(width=2000,height=2000)

    def saveFig(name):
        plt.savefig('figs\\'+name+'.png')
        plt.cla()
    
    