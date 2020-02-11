import matplotlib.pyplot as plt

class pltFunc(object):
    def addPolygon(poly):
        for i in range(0,len(poly)):
            if i == len(poly)-1:
                pltFunc.addLine([poly[i],poly[0]])
            else:
                pltFunc.addLine([poly[i],poly[i+1]])

    def addPolygonColor(poly):
        for i in range(0,len(poly)):
            if i == len(poly)-1:
                pltFunc.addLine([poly[i],poly[0]],color="blue")
            else:
                pltFunc.addLine([poly[i],poly[i+1]],color="blue")

    def addLine(line,**kw):
        if len(kw)==0:
            plt.plot([line[0][0],line[1][0]],[line[0][1],line[1][1]],color="black",linewidth=0.5)
        else:
            plt.plot([line[0][0],line[1][0]],[line[0][1],line[1][1]],color=kw["color"],linewidth=0.5)            
    
    def showPlt(**kw):
        if len(kw)>0:
            plt.axis([0,kw["width"],0,kw["height"]])
        else:
            plt.axis([0,2000,0,2000])
        plt.show()

    def saveFig(name):
        plt.savefig('figs\\'+name+'.jpg')
        plt.cla()