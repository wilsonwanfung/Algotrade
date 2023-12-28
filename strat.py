from AlgoAPI import AlgoAPIUtil, AlgoAPI_Backtest
from datetime import datetime, timedelta
import talib, numpy

#todo: learn divergence, know more about the rules of the contest

class AlgoEvent:
    def __init__(self):
        self.lasttradetime = datetime(2000,1,1)
        self.start_time = None # the starting time of the trading
        self.arr_close = numpy.array([])
            #self.arr_open = numpy.array([])
        self.ma_len = 20 # len of arrays of Moving Average
        self.rsi_len = 14 # len of window size in rsi calculation
        self.wait_time = self.ma_len # in days
        self.arr_bbw = numpy.array([])
        self.bbw_len = 1*30 # length of bbw, only set to 30 as too high will yield no sequeeze, may change

    def start(self, mEvt):
        self.myinstrument = mEvt['subscribeList'][0]
        self.evt = AlgoAPI_Backtest.AlgoEvtHandler(self, mEvt)
        self.evt.start()

    def on_bulkdatafeed(self, isSync, bd, ab):
        # set start time and arr_close(s) of all instruct. in bd on the first call of this function
        if not self.start_time:
            self.start_time = bd[self.myinstrument]['timestamp']
            for key in bd:
                bd[key]["arr_close"] = numpy.array([])
        
        # check if it is decision time
        if bd[self.myinstrument]['timestamp'] >= self.lasttradetime + timedelta(hours=24):
            # update arr_close(s)
            self.lasttradetime = bd[self.myinstrument]['timestamp']
            for key in bd:
                lastprice = bd[key]['lastPrice']
                bd[key]["arr_close"] = numpy.append(bd[key]["arr_close"], lastprice)
            
                # keep the most recent observations for arr_close (record of close prices)
                bd[key]["arr_close"] = bd[key]["arr_close"])[-self.ma_len::]
            
            # check if we have waited the initial peroid
            if bd[self.myinstrument]['timestamp'] <= self.start_time + timedelta(days = self.wait_time):
                return
            
            # find SMA, upper bband and lower bband, and bbw for the key
            for key in bd:
                sma = self.find_sma(bd[key][arr_close], self.ma_len)
                sd = numpy.std(bd[key][arr_close])
                upper_bband = sma + 2*sd
                lower_bband = sma - 2*sd
                bbw = (upper_bband-lower_bband)/sma
            
            
            
            #update bbw arr and determine if bollinger sequeeze
            self.arr_bbw = numpy.append(self.arr_bbw, bbw)
            self.arr_bbw = self.arr_bbw[-self.bbw_len::]
            #is_sequeeze = self.is_sequeeze(self.arr_bbw)
            is_sequeeze = False
            
            # debug print result
            self.evt.consoleLog(f"datetime: {bd[self.myinstrument]['timestamp']}")
            self.evt.consoleLog(f"sma: {sma}")
            self.evt.consoleLog(f"upper: {upper_bband}")
            self.evt.consoleLog(f"lower: {lower_bband}")
            self.evt.consoleLog(f"bbw: {bbw}")
            #self.evt.consoleLog(f"is squeeze?: {is_sequeeze}")
            
            # check for sell signal (price crosses upper bband and rsi > 70)
            if lastprice >= upper_bband:
                # caclulate the rsi
                rsi = self.find_rsi(self.arr_close, self.rsi_len)
                self.evt.consoleLog(f"rsi: {rsi}")
                # check for rsi
                if rsi > 60:
                    self.test_sendOrder(lastprice, -1, 'open', self.find_positionSize(lastprice, is_sequeeze))
                    self.evt.consoleLog(f"sell")
            
            # check for buy signal (price crosses lower bband and rsi < 30)
            if lastprice <= lower_bband:
                # caclulate the rsi
                rsi = self.find_rsi(self.arr_close, self.rsi_len)
                self.evt.consoleLog(f"rsi: {rsi}")
                # check for rsi
                if rsi < 40:
                    self.test_sendOrder(lastprice, 1, "open", self.find_positionSize(lastprice, is_sequeeze))
                    self.evt.consoleLog(f"buy")
                
            
            """
            # check number of record is at least greater than both self.fastperiod, self.slowperiod
            if not numpy.isnan(self.arr_fastMA[-1]) and not numpy.isnan(self.arr_fastMA[-2]) and not numpy.isnan(self.arr_slowMA[-1]) and not numpy.isnan(self.arr_slowMA[-2]):
                # send a buy order for Golden Cross
                if self.arr_fastMA[-1] > self.arr_slowMA[-1] and self.arr_fastMA[-2] < self.arr_slowMA[-2]:
                    self.test_sendOrder(lastprice, 1, 'open', find_positionSize(lastprice))
                # send a sell order for Death Cross
                if self.arr_fastMA[-1] < self.arr_slowMA[-1] and self.arr_fastMA[-2] > self.arr_slowMA[-2]:
                    self.test_sendOrder(lastprice, -1, 'open', find_positionSize(lastprice))
            """
            
            
    def on_marketdatafeed(self, md, ab):
        pass

    def on_orderfeed(self, of):
        pass

    def on_dailyPLfeed(self, pl):
        pass

    def on_openPositionfeed(self, op, oo, uo):
        pass
    
    
    def find_sma(self, data, window_size):
        return data[-window_size::].sum()/window_size

    # execute the trading strat for one instructment given the key and bd       
    def execute_strat(self, bd, key):
        # find sma, sd, 2 bbands, and bbw
        sma = self.find_sma(bd[key][arr_close], self.ma_len)
        sd = numpy.std(bd[key][arr_close])
        upper_bband = sma + 2*sd
        lower_bband = sma - 2*sd
        bbw = (upper_bband-lower_bband)/sma
        
        # debug
        self.evt.consoleLog(f"name of instrument: {bd[key]["instrument]}")
        self.evt.consoleLog(f"datetime: {bd[self.myinstrument]['timestamp']}")
        self.evt.consoleLog(f"sma: {sma}")
        self.evt.consoleLog(f"upper: {upper_bband}")
        self.evt.consoleLog(f"lower: {lower_bband}")
        self.evt.consoleLog(f"bbw: {bbw}")
        
        # check for sell signal (price crosses upper bband and rsi > 70)
    
        if lastprice >= upper_bband:
            # caclulate the rsi
            rsi = self.find_rsi(self.arr_close, self.rsi_len)
            self.evt.consoleLog(f"rsi: {rsi}")
            # check for rsi
            if rsi > 60:
                self.test_sendOrder(lastprice, -1, 'open', self.find_positionSize(lastprice, is_sequeeze))
                self.evt.consoleLog(f"sell")
        
    
    # determine if there is bollinger squeeze
    def is_sequeeze(self, arr_bbw):
        if len(arr_bbw) < self.bbw_len:
            return False
        return arr_bbw[-1] == arr_bbw.min()
    
    def find_rsi(self, arr_close, window_size):
        # we use previous day's close price as today's open price, which is not entirely accurate
        deltas = numpy.diff(arr_close)
        gains = deltas * (deltas > 0)
        losses = -deltas * (deltas < 0)
    
        avg_gain = numpy.mean(gains[:window_size])
        avg_loss = numpy.mean(losses[:window_size])
    
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
        return rsi
        
        
    def test_sendOrder(self, lastprice, buysell, openclose, volume = 10):
        order = AlgoAPIUtil.OrderObject()
        order.instrument = self.myinstrument
        order.orderRef = 1
        if buysell==1:
            order.takeProfitLevel = lastprice*1.1
            order.stopLossLevel = lastprice*0.9
        elif buysell==-1:
            order.takeProfitLevel = lastprice*0.9
            order.stopLossLevel = lastprice*1.1
        order.volume = volume
        order.openclose = openclose
        order.buysell = buysell
        order.ordertype = 0 #0=market_order, 1=limit_order, 2=stop_order
        self.evt.sendOrder(order)

     # utility function to find volume based on available balance
    def find_positionSize(self, lastprice, is_sequeeze):
        res = self.evt.getAccountBalance()
        availableBalance = res["availableBalance"]
        ratio = 0.3
        volume = (availableBalance*ratio) / lastprice
        total =  availableBalance*ratio
        while total < 0.3 * availableBalance:
            ratio *= 1.05
            volume = (availableBalance*ratio) / lastprice
            total = availableBalance*ratio
        while total > availableBalance:
            ratio *= 0.95
            volume = (availableBalance*ratio) / lastprice
            total = availableBalance*ratio
        if is_sequeeze:
            volume *= 5
        return volume*1000