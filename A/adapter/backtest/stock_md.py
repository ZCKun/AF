import os
import yaml
import pandas as pd

from A.types import KLine, Event, EventType, StrategyType, Price
from A.data import KLineHandle
from A.log import logger
from A.types.ctp import Snapshot

from glob import glob
from datetime import datetime
from multiprocessing import Queue
from typing import Optional
from numpy import char as nchar


def message_process(
        df: pd.DataFrame
) -> pd.DataFrame:
    data_df = df.rename(columns={
        'trayding_day': 'date',
        'ms': 'last_modified_mil',
        'time': 'last_modified',
        'Volume': 'volume',
    })
    last_modified_arr = data_df.last_modified.to_numpy(dtype=str)
    last_modified_mil_arr = data_df.last_modified_mil.to_numpy(dtype=str)
    last_modified_full_arr = nchar.add(nchar.add(last_modified_arr, '.'), last_modified_mil_arr)

    data_df.loc[:, 'last_modified_full'] = pd.to_datetime(df['datetime'], format="%Y-%m-%d %H:%M:%S.%f").dt.time
    # pd.to_datetime(last_modified_full_arr, format='%H:%M:%S.%f').time
    # data_df.loc[:, 'last_modified'] = data_df['last_modified_full']
    # pd.to_datetime(last_modified_arr, format='%H:%M:%S').time

    return data_df


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
        logger.debug(bar)
        event = Event()
        event.data = bar
        event.ex_type = StrategyType.CSV
        event.event_type = EventType.KLINE_DATA
        self._queue.put(event)

    def _data_pre_process(
            self,
            df: pd.DataFrame
    ) -> None:
        # date_time = pd.to_datetime(df.date + ' ' + df.time, format="%Y/%m/%d %H:%M:%S")
        date_time = pd.to_datetime(df.date + ' ' + df.time, format="%Y-%m-%d %H:%M:%S")
        df.loc[:, 'time'] = date_time.dt.time
        df.loc[:, 'date'] = date_time.dt.date
        df.loc[:, 'datetime'] = date_time
        df = df.rename(columns={
            "symbol": "symbol_code",
        })
        return df

    def _kline_msg_process(
            self,
            msg: pd.Series
    ) -> None:
        pass

    def _parser(
            self,
            df: pd.DataFrame
    ) -> None:
        logger.debug("_parser")
        for _, row in df.iterrows():
            symbol_code = row.symbol_code
            if symbol_code not in self._symbols:
                continue

            tick_data = Snapshot()
            tick_data.trading_day = row['date']# .replace('-', '')

            tick_data.instrument_id = row['symbol_code']
            tick_data.last_price = Price(row['last_price'])
            tick_data.open_price = Price(0)
            tick_data.high_price = Price(0)
            tick_data.low_price = Price(0)
            tick_data.close_price = Price(0)
            tick_data.open_interest = .0
            tick_data.update_time = row['time']
            tick_data.update_ms = row['ms']
            tick_data.volume = row['Volume']
            tick_data.turnover = row['turnover']

            tick_data.bid1_price = Price(0)
            tick_data.bid1_volume = 0
            tick_data.bid2_price = Price(0)
            tick_data.bid2_volume = 0
            tick_data.bid3_price = Price(0)
            tick_data.bid3_volume = 0
            tick_data.bid4_price = Price(0)
            tick_data.bid4_volume = 0
            tick_data.bid5_price = Price(0)
            tick_data.bid5_volume = 0

            tick_data.ask1_price = Price(0)
            tick_data.ask1_volume = 0
            tick_data.ask2_price = Price(0)
            tick_data.ask2_volume = 0
            tick_data.ask3_price = Price(0)
            tick_data.ask3_volume = 0
            tick_data.ask4_price = Price(0)
            tick_data.ask4_volume = 0
            tick_data.ask5_price = Price(0)
            tick_data.ask5_volume = 0

            event = Event()
            event.data = tick_data
            event.ex_type = StrategyType.CSV
            event.event_type = EventType.SNAPSHOT_DATA
            self._queue.put(event)

            df = pd.DataFrame([row.to_dict()])
            if symbol_code in self._source_cache:
                self._source_cache[symbol_code].append(df)
            else:
                self._source_cache[symbol_code] = [df]

            self._kline_handle_map[symbol_code].do(message_process(df))

    def _data_check(
            self,
            df: pd.DataFrame
    ) -> True:
        if 'last_price' not in df:
            logger.error("not found 'last_price' field.")
            return False
        return True

    def start(self):
        for file_path in self._source_files:
            df = pd.read_csv(file_path, encoding="utf-8")
            if not self._data_check(df):
                continue
            df = self._data_pre_process(df)
            self._parser(df)


def start(csv_config_path: str, queue: Queue, symbols: list[str]):
    logger.debug(f"symbols:{symbols}")
    config = yaml.safe_load(open(csv_config_path, encoding="utf-8"))
    md = StockMD(symbols, config['source_path'], queue)
    md.start()

