import os
import sys
import yaml
import pandas as pd

from A.log import logger
from A.sdk.xtp import QuoteApi
from A.data import KLineHandle
from A.types.xtp import Snapshot
from A.types import StrategyType
from A.types import KLine, EventType, Event
from A.sdk.xtp import XTP_EXCHANGE_TYPE, XTP_PROTOCOL_TYPE, XTP_LOG_LEVEL

from datetime import datetime
from multiprocessing import Queue


class Md(QuoteApi):

    def __init__(self, queue: Queue):
        super().__init__()
        self.trading_day = '-'
        self.data = {}
        self._queue = queue
        self._kline_handle_map: dict[str, KLineHandle] = {}

    def on_bar(self, bar: KLine):
        event = Event()
        event.data = bar
        event.ex_type = StrategyType.XTP
        event.event_type = EventType.KLINE_DATA
        self._queue.put(event)

    def on_disconnected(self, reason: int):
        """
        当客户端与行情后台通信连接断开时,该方法被调用
        :param reason: 错误原因,请与错误代码表对应
        """
        logger.error("<XTP> [on_disconnected] quote disconnected, reason:{reason}")
        sys.exit(1)

    def on_query_all_tickers_full_info(self, ticker_info: dict, error_info: dict, is_last: bool):
        """
        查询合约完整静态信息的应答

        :param ticker_info: 合约完整静态信息
        :param error_info: 查询合约完整静态信息时发生错误时返回的错误信息,当error_info为空,或者error_info.error_id为0时,表明没有错误
        :param is_last: 是否此次查询合约完整静态信息的最后一个应答,当为最后一个的时候为true,如果为false,表示还有其他后续消息响应
        """
        pass

    def on_query_all_tickers(self, ticker_info: dict, error_info: dict, is_last: bool):
        """
        查询合约部分静态信息的应答

        :param ticker_info: 合约部分静态信息
        :param error_info: 查询合约部分静态信息时发生错误时返回的错误信息,当error_info为空,或者error_info.error_id为0时,表明没有错误
        :param is_last: 是否此次查询合约部分静态信息的最后一个应答,当为最后一个的时候为true,如果为false,表示还有其他后续消息响应
        """
        pass

    def on_query_tickers_price_info(self, ticker_info: dict, error_info: dict, is_last: bool):
        """
        查询合约的最新价格信息应答

        :param ticker_info: 合约的最新价格信息
        :param error_info: 查询合约部分静态信息时发生错误时返回的错误信息,当error_info为空,或者error_info.error_id为0时,表明没有错误
        :param is_last: 是否此次查询合约部分静态信息的最后一个应答,当为最后一个的时候为true,如果为false,表示还有其他后续消息响应
        """
        pass

    def on_depth_market_data(self, market_data: dict, bid1_qty: list, bid1_count: int, max_bid1_count: int,
                             ask1_qty: list, ask1_count: int, max_ask1_count: int):
        """
        深度行情通知,包含买一卖一队列
        """
        tick = Snapshot(**market_data)
        tick.bid1_qty = bid1_qty
        tick.bid1_count = bid1_count
        tick.max_bid1_count = max_bid1_count
        tick.ask1_qty = ask1_qty
        tick.ask1_count = ask1_count
        tick.max_ask1_count = max_ask1_count
        event = Event()
        event.data = tick
        event.ex_type = StrategyType.XTP
        event.event_type = EventType.SNAPSHOT_DATA
        self._queue.put(event)

        df = pd.DataFrame([market_data])
        df['date'] = self.trading_day
        df = df.rename(columns={
            "ticker": "symbol_code",
            "last_price": "latest_price",
        })
        df.loc[:, 'last_modified_full'] = pd.to_datetime(df['data_time'], format="%Y%m%d%H%M%S%f").dt.time

        symbol_code = str(market_data['ticker']).strip()
        if symbol_code not in self._kline_handle_map:
            k = KLineHandle(symbol_code)
            k.subscribe(self.on_bar)
        else:
            k = self._kline_handle_map[symbol_code]
        k.do(df)

    def on_subscribe_all_market_data(self, exchange_id: int, error: dict):
        """
        订阅全市场的股票行情应答

        :param exchange_id: 表示当前全订阅的市场,如果为3,表示沪深全市场,1 表示为上海全市场,2 表示为深圳全市场
        :param error: 取消订阅合约时发生错误时返回的错误信息,当error_info为空,或者error_info.error_id为0时,表明没有错误
        """
        logger.info(f"<XTP> [on_subscribe_all_market_data] {exchange_id}")

    def on_sub_market_data(self, ticker: dict, error_info: dict, is_last: bool):
        """
        订阅行情应答,包括股票、指数和期权
        *每条订阅的合约均对应一条订阅应答,需要快速返回,否则会堵塞后续消息,当堵塞严重时,会触发断线

        :param ticker: 详细的合约订阅情况
        :param error_info: 订阅合约发生错误时的错误信息,当error_info为空,或者error_info.error_id为0时,表明没有错误
        :param is_last: 是否此次订阅的最后一个应答,当为最后一个的时候为true,如果为false,表示还有其他后续消息响应
        """
        self.data[ticker["ticker"]] = ticker
        logger.info(f"<XTP> [on_sub_market_data] {ticker}")


def start(config_path: str, queue: Queue, sub_symbol_codes: list[str]):
    xtp_config = yaml.safe_load(open(config_path, encoding="utf-8"))
    USER = xtp_config["user"]
    PASS = xtp_config["pass"]
    HOST = xtp_config["host"]
    PORT = xtp_config["port"]
    PROTOCOL_TYPE = xtp_config["socket_type"]
    CLIENT_ID = xtp_config["client_id"]

    md = Md(queue)
    md.create_quote_api(CLIENT_ID, os.getcwd(), XTP_LOG_LEVEL.XTP_LOG_LEVEL_DEBUG)
    if md.login(HOST, PORT, USER, PASS, PROTOCOL_TYPE, "0") != 0:
        logger.error(f"XTP Login failed! {md.get_api_last_error()}")
        sys.exit(1)

    logger.info(f"XTP Login Success, TradingDay: {md.get_trading_day()}")
    md.trading_day = md.get_trading_day()

    if len(sub_symbol_codes) == 0:
        # 订阅全市场行情快照
        s = md.subscribe_all_market_data(XTP_EXCHANGE_TYPE.XTP_EXCHANGE_UNKNOWN)
        if s != 0:
            err = md.get_api_last_error()
            logger.error(f"XTP Subscribe all market data failed, error:{err}")
        else:
            logger.info("XTP Subscribe all market data success.")
    else:
        sh_codes = []
        sz_codes = []
        sz_labels = ['30', '00', '12']
        for s in sub_symbol_codes:
            if s[:2] in sz_labels:
                sz_codes.append({'ticker': s})
            else:
                sh_codes.append({'ticker': s})

        if (count := len(sz_codes)) > 0:
            s = md.subscribe_market_data(sz_codes, count, XTP_EXCHANGE_TYPE.XTP_EXCHANGE_SZ)
            if s != 0:
                err = md.get_api_last_error()
                logger.error(f"XTP Subscribe SZ market data failed, error:{err}")
            else:
                logger.info("XTP Subscribe SZ market data success.")

        if (count := len(sh_codes)) > 0:
            s = md.subscribe_market_data(sh_codes, count, XTP_EXCHANGE_TYPE.XTP_EXCHANGE_SH)
            if s != 0:
                err = md.get_api_last_error()
                logger.error(f"XTP Subscribe SH market data failed, error:{err}")
            else:
                logger.info("XTP Subscribe SH market data success.")

    while int(datetime.now().strftime("%H%M%S")) <= 999999:  # 150200:
        pass


logger.info("XTP Work Done.")

if __name__ == "__main__":
    pass
