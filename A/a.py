from A.log import logger
from A.base.strategy.base import Strategy
from A.adapter import ctp_start, xtp_start, csv_start
from A.types import EventType, Event, StrategyType

from enum import Enum
from datetime import datetime
from multiprocessing import Queue, Process


class Mode(Enum):
    NORMAL = 1
    BACKTESTING = 2


class AF:

    def __init__(self,
                 ctp_config_path: str,
                 xtp_config_path: str,
                 csv_config_path: str,
                 run_mode: Mode,
                 enable_xtp: bool = False,
                 enable_ctp: bool = False
                 ):
        self._event_queue = Queue()
        self._strategies: list[Strategy] = list()
        self._ctp_config_path = ctp_config_path
        self._xtp_config_path = xtp_config_path
        self._csv_config_path = csv_config_path

        self._end_time = 999999
        self._run_mode = run_mode

        self._enable_xtp: bool = enable_xtp
        self._enable_ctp: bool = enable_ctp

    def docking(self, strategy: Strategy):
        if isinstance(strategy, Strategy):
            self._strategies.append(strategy)
        else:
            raise TypeError(f"not support strategy type: [{type(strategy)}].")

    def _on_bar(self, event: Event):
        for s in self._strategies:
            if s.type() == event.ex_type:
                s.on_bar(event.data)

    def _on_snapshot(self, event: Event):
        for s in self._strategies:
            if s.type() == event.ex_type:
                s.on_snapshot(event.data)

    def _get_symbol_codes(self, _type) -> list[str]:
        instrument_id = []

        for s in self._strategies:
            if s.type() == _type:
                instrument_id += s.sub_symbol_code

        return instrument_id

    def _on_event(self, event: Event):
        if event.event_type == EventType.SNAPSHOT_DATA:
            self._on_snapshot(event)
        elif event.event_type == EventType.KLINE_DATA:
            self._on_bar(event)

    def _start_with_normal(self):
        ctp_process = None
        xtp_process = None

        if self._enable_ctp:
            ctp_process = Process(target=ctp_start,
                                  args=(self._ctp_config_path,
                                        self._event_queue,
                                        self._get_symbol_codes(StrategyType.CTP))
                                  )
            ctp_process.start()

        if self._enable_xtp:
            xtp_process = Process(target=xtp_start,
                                  args=(self._xtp_config_path,
                                        self._event_queue,
                                        self._get_symbol_codes(StrategyType.XTP))
                                  )
            xtp_process.start()

        while int(datetime.now().strftime('%H%M%S')) < self._end_time:
            event: Event = self._event_queue.get()
            if not event:
                continue
            self._on_bar(event)

        if ctp_process is not None:
            ctp_process.join()
        if xtp_process is not None:
            xtp_process.terminate()

    def _start_with_backtesting(self):
        process = Process(target=csv_start,
                          args=(self._csv_config_path,
                                self._event_queue,
                                self._get_symbol_codes(StrategyType.CSV))
                          )
        process.start()
        process.join()

    def start(self):
        logger.info("AFramework start work")
        if self._run_mode == Mode.NORMAL:
            self._start_with_normal()
        elif self._run_mode == Mode.BACKTESTING:
            self._start_with_backtesting()
        logger.info("Framework work done.")
