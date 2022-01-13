import os
import yaml
import pandas as pd

from A.types import KLine, Event, EventType, StrategyType

from glob import glob
from multiprocessing import Queue


class CsvMd:
    def __init__(self, symbols: list[str], source_path: str, queue: Queue):
        if os.path.isdir(source_path):
            self._source_files = glob(os.path.join(source_path, "*.csv"))
            # 以文件名排序
            self._source_files = sorted(self._source_files,
                                        key=lambda x: os.path.splitext(os.path.split(x)[-1])[0])
        else:
            self._source_files: list[str] = [source_path]

        self._queue: Queue = queue
        self._symbols: list[str] = symbols

    def _on_bar(self, bar: KLine):
        event = Event()
        event.data = bar
        event.ex_type = StrategyType.CSV
        event.event_type = EventType.KLINE_DATA
        self._queue.put(event)

    def _parser(self, df: pd.DataFrame):
        for _, row in df.iterrows():
            if row.symbol not in self._symbols:
                continue

    def start(self):
        for file_path in self._source_files:
            df = pd.read_csv(file_path, encoding="utf-8")
            self._parser(df)


def start(csv_config_path: str, queue: Queue, symbols: list[str]):
    config = yaml.safe_load(open(csv_config_path, encoding="utf-8"))
    md = CsvMd(symbols, config['source_path'], queue)
