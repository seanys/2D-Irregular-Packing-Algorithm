import time

class OutputFunc(object):
    '''输出不同颜色字体'''
    @staticmethod
    def outputWarning(prefix,_str):
        '''输出红色字体'''
        _str = prefix + str(time.strftime("%H:%M:%S", time.localtime())) + " " + str(_str)
        print("\033[0;31m",_str,"\033[0m")

    @staticmethod
    def outputAttention(prefix,_str):
        '''输出绿色字体'''
        _str = prefix + str(time.strftime("%H:%M:%S", time.localtime())) + " " + str(_str)
        print("\033[0;32m",_str,"\033[0m")

    @staticmethod
    def outputInfo(prefix,_str):
        '''输出浅黄色字体'''
        _str = prefix + str(time.strftime("%H:%M:%S", time.localtime())) + " " + str(_str)
        print("\033[0;33m",_str,"\033[0m")
