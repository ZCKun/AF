import os
import yaml
import pandas as pd

from A.types import KLine, Event, EventType, StrategyType
from A.data import KLineHandle
from A.log import logger

from glob import glob
from datetime import datetime
from multiprocessing import Queue


class CsvMd:
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
        date_time = pd.to_datetime(df.date + ' ' + df.time, format="%Y/%m/%d %H:%M:%S")
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

            bar = KLine()
            bar.symbol_code = row.symbol_code
            bar.time = row.time
            dt = row.datetime
            bar.datetime = datetime(year=dt.year,
                                    month=dt.month,
                                    day=dt.day,
                                    hour=dt.hour,
                                    minute=dt.minute,
                                    second=dt.second)
            bar.open = row.open
            bar.high = row.high
            bar.low = row.low
            bar.close = row.close
            bar.volume = row.volume
            bar.turnover = row.money
            bar.style = 1 if row.open > row.close else -1

            event = Event()
            event.data = bar
            event.ex_type = StrategyType.CSV
            event.event_type = EventType.KLINE_DATA
            self._queue.put(event)
            # if symbol_code not in self._kline_handle_map:
            #     k = KLineHandle(symbol_code, t0_date=row.date)
            #     k.subscribe(self._on_bar)
            #     self._kline_handle_map[symbol_code] = k
            # else:
            #     k = self._kline_handle_map[symbol_code]
            # k.do(row)

    def _data_check(
            self,
            df: pd.DataFrame
    ) -> True:
        if 'symbol' not in df:
            logger.error("not found 'symbol' field.")
            return False
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
    md = CsvMd(symbols, config['source_path'], queue)
    md.start()
