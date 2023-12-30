from AlgoAPI import AlgoAPIUtil, AlgoAPI_Backtest
from datetime import datetime, timedelta
import talib, numpy

#todo: learn divergence, know more about the rules of the contest

class AlgoEvent:
    def __init__(self):
        self.lasttradetime = datetime(2000,1,1)
        self.start_time = None # the starting time of the trading
        self.ma_len = 20 # len of arrays of Moving Average
        self.rsi_len = 14 # len of window size in rsi calculation
        self.wait_time = self.ma_len # in days
        self.arr_bbw = numpy.array([])
        self.bbw_len = 1*30 # length of bbw, only set to 30 as too high will yield no sequeeze, may change
        self.arr_close_dict = {} # key to the corresponding arr_close
        self.inst_data = {} # for storing data of the instruments
        self.general_period = 14 # general period for indicator 
        self.fastperiod = 5 #??
        self.midperiod = 8 #??
        self.slowperiod = 13 #??
         
        self.risk_reward_ratio = 2 # take profit level : risk_reward_ratio * stoploss
        self.stoploss_atrlen = 2 # width of atr for stoplsos
        self.allocationratio_per_trade = 0.3
 

    def start(self, mEvt):
        self.myinstrument = mEvt['subscribeList'][0]
        self.evt = AlgoAPI_Backtest.AlgoEvtHandler(self, mEvt)
        self.evt.start()


    def on_bulkdatafeed(self, isSync, bd, ab):
        # see if sync
        if not isSync:
            return
            
        # set start time and inst_data in bd on the first call of this function
        if not self.start_time:
            self.start_time = bd[self.myinstrument]['timestamp']
            for key in bd:
                self.inst_data[key] = {
                    "arr_close": numpy.array([]),
                    "high_price": numpy.array([]),
                    "low_price": numpy.array([]),
                    'arr_fastMA': numpy.array([]),
                    'arr_midMA': numpy.array([]),
                    'arr_slowMA': numpy.array([]),
                    'atr': numpy.array([])
                }
                
                
        # check if it is decision time
        if bd[self.myinstrument]['timestamp'] >= self.lasttradetime + timedelta(hours=24):
            # update inst_data's arr close, highprice and lowprice, and MA lines
            self.lasttradetime = bd[self.myinstrument]['timestamp']
            for key in bd:
                inst_data = self.inst_data[key]
                inst_data['high_price'] = numpy.append(inst_data['high_price'], bd[key]['highPrice'])
                inst_data['arr_close'] = numpy.append(inst_data['arr_close'], bd[key]['lastPrice'])
                inst_data['low_price'] = numpy.append(inst_data['low_price'], bd[key]['lowPrice'])
                
                time_period = self.ma_len * 2
                # keep the most recent observations for arr_close (record of close prices)
                inst_data['high_price'] = inst_data['high_price'][-time_period::]
                inst_data['arr_close'] = inst_data['arr_close'][-time_period::]
                inst_data['low_price'] = inst_data['low_price'][-time_period::]
                
                inst_data['atr'] = talib.ATR(inst_data['high_price'], inst_data['low_price'], inst_data['arr_close'], timeperiod = self.general_period)
                
            # check if we have waited the initial peroid
            if bd[self.myinstrument]['timestamp'] <= self.start_time + timedelta(days = self.wait_time):
                return
            
            # execute the trading strat for all instruments
            for key in bd:
                self.execute_strat(bd, key)
            
            
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
        
    def rangingFilter(self, ADXR, AROONOsc, MA_same_direction, rsi):
        lowest_rsi, highest_rsi = min(rsi), max(rsi)
        maxchange_rsi = max(abs(rsi[-1] - lowest_rsi), abs(rsi[-1] - highest_rsi), 0)
        maxchange_ADXR = ADXR[-1] - min(ADXR)
        if (ADXR[-1] < 20) or abs(AROONOsc[-1]) < 20 or 40 < rsi[-1] < 60 :
            return True # ranging market
        else:
            return False

    # execute the trading strat for one instructment given the key and bd       
    def execute_strat(self, bd, key):
        self.evt.consoleLog("---------------------------------")
        self.evt.consoleLog("Executing strat")

        # find sma, sd, 2 bbands, bbw, and lastprice
        inst = self.inst_data[key]
        arr_close = inst['arr_close']
        sma = self.find_sma(arr_close, self.ma_len)
        sd = numpy.std(arr_close)
        upper_bband = sma + 2*sd
        lower_bband = sma - 2*sd
        bbw = (upper_bband-lower_bband)/sma
        lastprice = arr_close[-1]
        
        # calculate MA same direction?
        fast, mid, slow = inst['arr_fastMA'], inst['arr_midMA'], inst['arr_slowMA']
        all_MA_up, all_MA_down, MA_same_direction = False, False, False
        if len(fast) > 1 and len(mid) > 1 and len(slow) > 1:
            all_MA_up = fast[-1] > fast[-2] and mid[-1] > mid[-2] and slow[-1] > slow[-2]
            all_MA_down = fast[-1] < fast[-2] and mid[-1] < mid[-2] and slow[-1] < slow[-2]
            MA_same_direction = all_MA_up or all_MA_down
            
        
        # ranging filter (to confirm moving sideway)
        adxr = talib.ADXR(inst['high_price'], inst['low_price'], inst['arr_close'], 
            timeperiod=self.general_period)
        apo = talib.APO(inst['arr_close'], self.midperiod, self.slowperiod)
        macd, signal, hist = talib.MACD(inst['arr_close'], self.fastperiod, self.slowperiod, self.midperiod)
        rsiFast, rsiGeneral = talib.RSI(inst['arr_close'], self.fastperiod), talib.RSI(inst['arr_close'], self.general_period)       
        # Calculate Aroon values
        aroon_up, aroon_down = talib.AROON(inst['high_price'], inst['low_price'], timeperiod=self.general_period)
        aroonosc = aroon_up - aroon_down
        
        ranging = self.rangingFilter(adxr, aroonosc, MA_same_direction, rsiGeneral)
        
        
        #sequeeze? (maybe remove)
        #is_sequeeze = False
        #self.arr_bbw = numpy.append(self.arr_bbw, bbw)
        #self.arr_bbw = self.arr_bbw[-self.bbw_len::]
        #is_sequeeze = self.is_sequeeze(self.arr_bbw)
        
        # debug
        self.evt.consoleLog(f"name of instrument: { bd[key]['instrument'] }")
        #self.evt.consoleLog(f"datetime: {bd[self.myinstrument]['timestamp']}")
        #self.evt.consoleLog(f"sma: {sma}")
        #self.evt.consoleLog(f"upper: {upper_bband}")
        #self.evt.consoleLog(f"lower: {lower_bband}")
        #self.evt.consoleLog(f"bbw: {bbw}")
        
        # check for sell signal (price crosses upper bband and rsi > 70)
    
        if lastprice >= upper_bband:
            # caclulate the rsi
            atr =  inst['atr'][-1]
            stoploss = self.stoploss_atrlen * atr
            rsi = talib.RSI(inst["arr_close"], self.general_period)
            # check for rsi
            if True:
                self.test_sendOrder(lastprice, -1, 'open', stoploss, self.find_positionSize(lastprice))
                self.evt.consoleLog(f"SELL SELL SELL SELL")
                
        # check for buy signal (price crosses lower bband and rsi < 30)
        if lastprice <= lower_bband:
            # caclulate the rsi
            atr =  inst['atr'][-1]
            stoploss = self.stoploss_atrlen * atr
            rsi = talib.RSI(inst["arr_close"], self.general_period)
            # check for rsi
            if True:
                self.test_sendOrder(lastprice, 1, "open", stoploss, self.find_positionSize(lastprice))
                self.evt.consoleLog(f"BUY BUY BUY BUY")
                
        self.evt.consoleLog("Executed strat")
        self.evt.consoleLog("---------------------------------")

        
        
        
    # determine if there is bollinger squeeze
    def is_sequeeze(self, arr_bbw):
        if len(arr_bbw) < self.bbw_len:
            return False
        return arr_bbw[-1] == arr_bbw.min()
    
        

    def test_sendOrder(self, lastprice, buysell, openclose, stoploss, volume = 10):
        order = AlgoAPIUtil.OrderObject()
        order.instrument = self.myinstrument
        order.orderRef = 1
        if buysell==1:
            order.takeProfitLevel = lastprice +  self.risk_reward_ratio * stoploss
            order.stopLossLevel = lastprice - stoploss 
        elif buysell==-1:
            order.takeProfitLevel = lastprice - self.risk_reward_ratio * stoploss
            order.stopLossLevel = lastprice + stoploss
        order.volume = volume
        order.openclose = openclose
        order.buysell = buysell
        order.ordertype = 0 #0=market_order, 1=limit_order, 2=stop_order
        self.evt.sendOrder(order)

      # utility function to find volume based on available balance
    def find_positionSize(self, lastprice):
        res = self.evt.getAccountBalance()
        availableBalance = res["availableBalance"]
        ratio = self.allocationratio_per_trade
        volume = (availableBalance*ratio) / lastprice
        total =  volume *  lastprice
        while total < self.allocationratio_per_trade * availableBalance:
            ratio *= 1.05
            volume = (availableBalance*ratio) / lastprice
            total =  volume *  lastprice
        while total > availableBalance:
            ratio *= 0.95
            volume = (availableBalance*ratio) / lastprice
            total =  volume *  lastprice
        return volume
