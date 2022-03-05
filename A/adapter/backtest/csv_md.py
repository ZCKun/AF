import os
import re
import time

import yaml
import pandas as pd

from A.types import KLine, Event, EventType, StrategyType, Price
from A.data import KLineHandle
from A.log import logger
from A.types.stock import Snapshot, OrderBook

from glob import glob
from datetime import datetime
from multiprocessing import Queue
from typing import Optional
from numpy import char as nchar


class StockMD:
    def __init__(
            self,
            symbols: list[str],
            source_path: str,
            queue: Queue
    ) -> None:
        if os.path.isdir(source_path):
            self._source_files = glob(os.path.join(source_path, "*.csv"))
            # sort by filename
            self._source_files = sorted(self._source_files,
                                        key=lambda x: os.path.splitext(os.path.split(x)[-1])[0])
        else:
            self._source_files: list[str] = [source_path]

        self._queue: Queue = queue
        self._symbols: list[str] = symbols
        self._kline_handle_map: dict[str, KLineHandle] = dict()
        self._last_bar: Optional[KLine] = None
        self._source_cache: dict = dict()

        self._data_check_pattern: re.Pattern = re.compile(r"\[(tick|trade|order|orderbook)]")
        self._parser_map: dict = dict(
            tick=self._tick_parser,
            order=self._order_parser,
            trade=self._trade_parser,
            orderbook=self._ob_parser,
        )
        self._last_snapshot_map: dict[str, Snapshot] = dict()

        self._init()

    def _init(self):
        for symbol in self._symbols:
            k = KLineHandle(symbol)
            k.subscribe(self._on_bar)
            self._kline_handle_map[symbol] = k

    def _on_bar(
            self,
            bar: KLine
    ) -> None:
        event = Event()
        event.data = bar
        event.ex_type = StrategyType.STOCK
        event.event_type = EventType.KLINE_DATA
        self._queue.put(event)

    def _kline_msg_process(
            self,
            msg: pd.Series
    ) -> None:
        pass

    def _tick_parser(self, content: str):
        items = content.split(',')

        now_time = int(f"{items[1]}{items[2]}")
        symbol_code = items[3]
        if symbol_code not in self._symbols:
            return

        data_time = datetime.strptime(items[4], "%Y%m%d%H%M%S%f")
        pre_close_price = float(items[5])
        open_price = float(items[6])
        high_price = float(items[7])
        low_price = float(items[8])
        last_price = float(items[9])
        total_trade_vol = int(items[11])
        total_trade_turnover = float(items[12])
        upper_limit_price = float(items[13])
        lower_limit_price = float(items[14])

        ask: list = []
        ask_qty: list = []
        bid: list = []
        bid_qty: list = []
        for i in range(15, 55, 4):
            ask.append(float(items[i]))
            ask_qty.append(int(float(items[i + 1])))
            bid.append(float(items[i + 2]))
            bid_qty.append(int(float(items[i + 3])))

        if symbol_code in self._last_snapshot_map:
            last_snapshot = self._last_snapshot_map[symbol_code]
        else:
            last_snapshot = Snapshot()
            last_snapshot.total_trade_volume = .0
            last_snapshot.total_trade_turnover = .0

        snapshot = Snapshot()
        snapshot.symbol_code = symbol_code
        snapshot.data_time = data_time
        snapshot.recv_time = now_time
        snapshot.pre_close_price = pre_close_price
        snapshot.open_price = open_price
        snapshot.high_price = high_price
        snapshot.low_price = low_price
        snapshot.last_price = last_price
        snapshot.trade_volume = total_trade_vol - last_snapshot.total_trade_volume
        snapshot.trade_turnover = total_trade_turnover - last_snapshot.total_trade_turnover
        snapshot.total_trade_volume = total_trade_vol
        snapshot.total_trade_turnover = total_trade_turnover
        snapshot.upper_limit_price = upper_limit_price
        snapshot.lower_limit_price = lower_limit_price
        snapshot.bid = bid
        snapshot.ask = ask
        snapshot.bid_qty = bid_qty
        snapshot.ask_qty = ask_qty

        self._last_snapshot_map[symbol_code] = snapshot

        event = Event()
        event.data = snapshot
        event.event_type = EventType.SNAPSHOT_DATA
        event.ex_type = StrategyType.STOCK
        self._queue.put(event)

        df = pd.DataFrame([snapshot])
        df = df.rename(columns={
            "trade_volume": "volume",
        })
        self._kline_handle_map[snapshot.symbol_code].do(df.iloc[0])

    def _trade_parser(self, content: str):
        pass

    def _order_parser(self, content: str):
        pass

    def _ob_parser(self, content: str):
        items = content.split(',')

        now_time = int(f"{items[1]}{items[2]}")
        symbol_code = items[3]
        if symbol_code not in self._symbols:
            return

        order_book = OrderBook()
        order_book.symbol_code = symbol_code
        order_book.recv_time = now_time

        order_book.data_time = datetime.strptime(items[4], "%Y%m%d%H%M%S%f")
        order_book.last_price = float(items[5])
        order_book.qty = int(items[6])
        order_book.turnover = float(items[7])
        order_book.trades_count = int(items[8])

        ob_items = [i for i in items[9:] if i.strip()]
        ob_len = len(ob_items)
        bids: list[tuple] = []
        asks: list[tuple] = []
        for i in range(0, ob_len, 4):
            bp = float(ob_items[i])
            bq = int(ob_items[i+1])
            ap = float(ob_items[i+2])
            aq = int(ob_items[i+3])
            bids.append((bp, bq))
            asks.append((ap, aq))

        order_book.bids = bids
        order_book.asks = asks

        event = Event()
        event.event_type = EventType.ORDERBOOK_DATA
        event.data = order_book
        event.ex_type = StrategyType.STOCK
        self._queue.put(event)

    def _parser(
            self,
            item: str
    ) -> None:
        m = self._data_check_pattern.findall(item)
        if len(m) == 0:
            return

        self._parser_map[m[0]](item)

    def start(self):
        for file_path in self._source_files:
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    self._parser(line)
        self._queue.put("Done")


def start(csv_config_path: str, queue: Queue, symbols: list[str]):
    config = yaml.safe_load(open(csv_config_path, encoding="utf-8"))
    md = StockMD(symbols, config['source_path'], queue)
    md.start()
