import os
import sys
import time
import yaml
import pandas as pd

from A.types import Price, EventType, Event, StrategyType
from A.types.ctp import Snapshot
from numpy import char as nchar
from datetime import datetime
from ctpwrapper import MdApiPy, ApiStructure
from ctpwrapper.ApiStructure import DepthMarketDataField
from multiprocessing import Queue

from A.log import logger
from A.data import KLineHandle

TODAY_DT = datetime.today()
TODAY_DT_STR = TODAY_DT.strftime('%Y%m%d')


def message_process(df: pd.DataFrame):
    data_df = df.rename(columns={
        'InstrumentID': 'symbol_code',
        'TradingDay': 'date',
        'LastPrice': 'last_price',
        'UpdateMillisec': 'last_modified_mil',
        'UpdateTime': 'last_modified'
    })
    last_modified_arr = data_df.last_modified.to_numpy(dtype=str)
    last_modified_mil_arr = data_df.last_modified_mil.to_numpy(dtype=str)
    last_modified_full_arr = nchar.add(nchar.add(last_modified_arr, '.'), last_modified_mil_arr)

    data_df.loc[:, 'last_modified_full'] = pd.to_datetime(last_modified_full_arr, format='%H:%M:%S.%f').time
    data_df.loc[:, 'last_modified'] = pd.to_datetime(last_modified_arr, format='%H:%M:%S').time

    return data_df


class MarketSpi(MdApiPy):

    def __init__(self, config: dict, queue: Queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._login = False
        self._queue: Queue = queue

        self._broker_id = config["broker_id"]
        self._investor_id = config["investor_id"]
        self._password = config["password"]
        self._user_product_info = config["user_product_info"]
        self._auth_code = config['auth_code']
        self._app_id = config['app_id']
        self._instrument_id = config["instrument_id"]

        self._request_id = 0
        self._source_cache = {}
        self._kline_handle_map: dict[str, KLineHandle] = dict()

    def is_login(self) -> bool:
        return self._login

    def on_bar(self, bar):
        event = Event()
        event.data = bar
        event.ex_type = StrategyType.CTP
        event.event_type = EventType.KLINE_DATA
        self._queue.put(event)

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
        logger.debug("<CTP> front address connected, start login.")
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

        tick_data = Snapshot()
        tick_data.instrument_id = depth_market_data.InstrumentID
        tick_data.last_price = Price(depth_market_data.LastPrice)
        tick_data.open_price = Price(depth_market_data.OpenPrice)
        tick_data.high_price = Price(depth_market_data.HighestPrice)
        tick_data.low_price = Price(depth_market_data.LowestPrice)
        tick_data.close_price = Price(depth_market_data.ClosePrice)
        tick_data.open_interest = depth_market_data.OpenInterest
        tick_data.update_time = depth_market_data.UpdateTime
        tick_data.update_ms = depth_market_data.UpdateMillisec
        tick_data.volume = depth_market_data.Volume
        tick_data.turnover = Price(depth_market_data.Turnover)

        tick_data.bid1_price = Price(depth_market_data.BidPrice1)
        tick_data.bid1_volume = depth_market_data.BidVolume1
        tick_data.bid2_price = Price(depth_market_data.BidPrice2)
        tick_data.bid2_volume = depth_market_data.BidVolume2
        tick_data.bid3_price = Price(depth_market_data.BidPrice3)
        tick_data.bid3_volume = depth_market_data.BidVolume3
        tick_data.bid4_price = Price(depth_market_data.BidPrice4)
        tick_data.bid4_volume = depth_market_data.BidVolume4
        tick_data.bid5_price = Price(depth_market_data.BidPrice5)
        tick_data.bid5_volume = depth_market_data.BidVolume5

        tick_data.ask1_price = Price(depth_market_data.AskPrice1)
        tick_data.ask1_volume = depth_market_data.AskVolume1
        tick_data.ask2_price = Price(depth_market_data.AskPrice2)
        tick_data.ask2_volume = depth_market_data.AskVolume2
        tick_data.ask3_price = Price(depth_market_data.AskPrice3)
        tick_data.ask3_volume = depth_market_data.AskVolume3
        tick_data.ask4_price = Price(depth_market_data.AskPrice4)
        tick_data.ask4_volume = depth_market_data.AskVolume4
        tick_data.ask5_price = Price(depth_market_data.AskPrice5)
        tick_data.ask5_volume = depth_market_data.AskVolume5

        event = Event()
        event.data = tick_data
        event.ex_type = StrategyType.CTP
        event.event_type = EventType.SNAPSHOT_DATA
        self._queue.put(event)

        df = pd.DataFrame([depth_market_data.to_dict()])
        if symbol_code in self._source_cache:
            self._source_cache[symbol_code].append(df)
        else:
            self._source_cache[symbol_code] = [df]

        self._kline_handle_map[symbol_code].do(message_process(df))

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
        instrument_id = specific_instrument.InstrumentID
        k = KLineHandle(instrument_id)
        k.subscribe(self.on_bar)
        self._kline_handle_map[instrument_id] = k

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
        pass

    def save(self):
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


def start(config_path: str, queue: Queue, sub_instrument_id: list[str]):
    """ 创建并启动 CTP 实例

    :param config_path: ctp 配置路径
    :param queue: 事件驱动消息队列
    :param sub_instrument_id: 需要订阅的合约代码
    :return:
    """
    config = yaml.safe_load(open(config_path, encoding="utf-8"))
    market_servers = config["md_server"]

    logger.info("start create the ctp instance.")
    market = MarketSpi(config, queue)
    market.Create("./cache")

    for server in market_servers:
        market.RegisterFront(server)
        logger.info(f"ctp front address {server} registered.")
    market.Init()

    logger.info("ctp instance created.")
    trading_day = market.GetTradingDay()
    logger.info(f"<CTP> trading day: {trading_day}")

    if market.is_login():
        market.SubscribeMarketData(sub_instrument_id)
        stop_time: int = int(config['stop_time']) if 'stop_time' in config else 150500
        while True:
            if int(datetime.now().strftime('%H%M%S')) >= stop_time:
                market.UnSubscribeMarketData(sub_instrument_id)
                break
            time.sleep(1)
    else:
        logger.error(f"<CTP> login fail.")

    market.save()
    logger.info("ctp work done.")


if __name__ == "__main__":
    pass
