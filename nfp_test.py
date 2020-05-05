import json
from tools.geofunc import GeoFunc
from tools.nfp import NFP
import pandas as pd

# 计算NFP然后寻找最合适位置
def tryNFP():
    df = pd.read_csv("data/blaz1.csv")

    poly1=json.loads(df['polygon'][1])
    poly2=json.loads(df['polygon'][2])
    GeoFunc.normData(poly1,50)
    GeoFunc.normData(poly2,50)
    GeoFunc.slidePoly(poly1,500,500)

    nfp=NFP(poly1,poly2,show=True)
    print(nfp.nfp)

if __name__ == '__main__':
    # PlacePolygons(getData())
    tryNFP()