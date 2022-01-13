import os
import sys
import time
import yaml
import pandas as pd

from numpy import char as nchar
from datetime import datetime
from ctpwrapper import MdApiPy, ApiStructure
from ctpwrapper.ApiStructure import DepthMarketDataField

from A.log import logger
from A.data import KLineHandle

TODAY_DT = datetime.today()
TODAY_DT_STR = TODAY_DT.strftime('%Y%m%d')


class MarketSpi(MdApiPy):

    def __init__(self, config: dict, queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._login = False
        self._queue = queue

        self._broker_id = config["broker_id"]
        self._investor_id = config["investor_id"]
        self._password = config["password"]
        self._user_product_info = config["user_product_info"]
        self._auth_code = config['auth_code']
        self._app_id = config['app_id']
        self._instrument_id = config["instrument_id"]

        self._request_id = 0
        self._source_cache = {}
        self._kline_handle = KLineHandle(self._instrument_id)
        self._kline_handle.subscribe(self.on_bar)

    def on_bar(self, bar):
        self._queue.put(bar)

    @property
    def request_id(self):
        self._request_id += 1
        return self._request_id

    def OnRspError(self, pRspInfo, nRequestID, bIsLast):
        logger.error("<CTP> [OnRspError] Info:{pRspInfo}, RequestID:{nRequestID}, IsLast:{bIsLast}")

    def OnFrontConnected(self):
        """
        :return:
        """
        user_login = ApiStructure.ReqUserLoginField(BrokerID=self._broker_id,
                                                    UserID=self._investor_id,
                                                    Password=self._password)
        self.ReqUserLogin(user_login, self.request_id)

    def OnFrontDisconnected(self, nReason):
        logger.error(f"<CTP> [OnFrontDisconnected] Md OnFrontDisconnected, Reason:{nReason}")
        sys.exit()

    def OnHeartBeatWarning(self, nTimeLapse):
        """心跳超时警告。当长时间未收到报文时，该方法被调用。
        @param nTimeLapse 距离上次接收报文的时间
        """
        logger.error(f"<CTP> [OnHeartBeatWarning] Md OnHeartBeatWarning, time:{nTimeLapse}")

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, pRequestID, bIsLast):
        """
        用户登录应答
        :param pRspUserLogin:
        :param pRspInfo:
        :param pRequestID:
        :param bIsLast:
        :return:
        """
        if pRspInfo.ErrorID != 0:
            logger.error(f"X Login Failed, RspUserLogin:{pRspUserLogin}, RspInfo: {pRspInfo}, RequestID:{pRequestID}")
        else:
            self._login = True
            logger.info(f"✓ Login Successfully, RspUserLogin:{pRspUserLogin}, RspInfo: {pRspInfo}")

    def OnRtnDepthMarketData(self, depth_market_data: DepthMarketDataField):
        """
        行情订阅推送信息
        :param depth_market_data:
        :return:
        """
        symbol_code = depth_market_data.InstrumentID
        if symbol_code != self._instrument_id:
            return

        open_price = round(depth_market_data.OpenPrice, 3)
        close_price = round(float(depth_market_data.ClosePrice), 1)
        high_price = round(depth_market_data.HighestPrice, 3)
        low_price = round(depth_market_data.LowestPrice, 3)
        volume = depth_market_data.Volume
        turnover = depth_market_data.Turnover
        open_interest = depth_market_data.OpenInterest
        update_time = depth_market_data.UpdateTime
        update_mil = depth_market_data.UpdateMillisec
        last_price = round(depth_market_data.LastPrice, 3)

        # print(
        # f"UpdateTime:{update_time}.{update_mil}, 股票代码:{symbol_code}, 开盘价:{open_price}, 最高价:{high_price}, 最低价:{low_price}, 最新价:{last_price}, "
        # f"量:{volume}, 成交金额:{turnover}, 持仓量:{open_interest}")
        df = pd.DataFrame([depth_market_data.to_dict()])
        if symbol_code in self._source_cache:
            self._source_cache[symbol_code].append(df)
        else:
            self._source_cache[symbol_code] = [df]
        self._kline_handle.do(self.message_process(df))

        '''
        {'start_datetime': datetime.time(9, 51, 28, 500000), 'end_datetime': datetime.time(9, 52, 27, 500000), 'date': datetime.datetime(2021, 12, 1, 9, 52, 27, 677138), 'style': 1, 'open': 4831.4, 'high': 4833.4, 'low': 4829.0, 'close': 4833.2, 'volume': 0}
        '''

    def OnRspSubMarketData(self, specific_instrument, rsp_info, request_id, is_last):
        """
        订阅行情应答
        :param specific_instrument:
        :param rsp_info:
        :param request_id:
        :param is_last:
        :return:
        """
        # print("OnRspSubMarketData")
        # print("RequestId:", request_id)
        # print("isLast:", is_last)
        # print("pRspInfo:", rsp_info)
        # print("pSpecificInstrument:", specific_instrument)
        pass

    def OnRspUnSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        """
        取消订阅行情应答
        :param pSpecificInstrument:
        :param pRspInfo:
        :param nRequestID:
        :param bIsLast:
        :return:
        """
        # print("OnRspUnSubMarketData")
        # print("RequestId:", nRequestID)
        # print("isLast:", bIsLast)
        # print("pRspInfo:", pRspInfo)
        # print("pSpecificInstrument:", pSpecificInstrument)
        self.save()

    def message_process(self, df):
        data_df = df.rename(columns={
            'InstrumentID': 'symbol_code',
            'TradingDay': 'date',
            'LastPrice': 'latest_price',
            'UpdateMillisec': 'last_modified_mil',
            'UpdateTime': 'last_modified'
        })
        last_modified_arr = data_df.last_modified.to_numpy(dtype=str)
        last_modified_mil_arr = data_df.last_modified_mil.to_numpy(dtype=str)
        last_modified_full_arr = nchar.add(nchar.add(last_modified_arr, '.'), last_modified_mil_arr)

        data_df.loc[:, 'last_modified_full'] = pd.to_datetime(last_modified_full_arr, format='%H:%M:%S.%f').time
        data_df.loc[:, 'last_modified'] = pd.to_datetime(last_modified_arr, format='%H:%M:%S').time

        return data_df

    def save(self):
        return
        if not os.path.exists(TODAY_DT_STR):
            os.mkdir(TODAY_DT_STR)

        now_time = int(datetime.now().strftime('%H%M%S'))
        if 40000 > now_time > 23000:
            suffix = '_night'
        else:
            suffix = ''

        for symbol_code, value in self._source_cache.items():
            df = pd.concat(value)
            df.to_csv(f'{TODAY_DT_STR}/{symbol_code}{suffix}.csv', encoding='utf-8')

    def __del__(self):
        self.save()


def start(config_path, queue):
    config = yaml.safe_load(open(os.path.join(config_path, "ctp_config.yaml"), encoding="utf-8"))
    market_servers = config["md_server"]
    year_months = config['year_month']
    markets = config['markets']

    symbol_codes = []
    for year_month in year_months:
        for market in markets:
            sc = market + year_month
            symbol_codes.append(sc)

    market = MarketSpi(config, queue)
    market.Create()
    for server in market_servers:
        market.RegisterFront(server)
    market.Init()
    trading_day = market.GetTradingDay()
    logger.info(f"trading day: {trading_day}")

    if market._login:
        market.SubscribeMarketData(symbol_codes)
        while True:
            if int(datetime.now().strftime('%H%M%S')) >= 150200:
                market.UnSubscribeMarketData(symbol_codes)
                break
            time.sleep(1)
    else:
        pass


def on_kline(bar):
    pass


if __name__ == "__main__":
    start("config", on_kline)
