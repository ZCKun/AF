from A.log import logger
from A.base.strategy.base import Strategy
from A.adapter import ctp_start, xtp_start
from A.types import EventType, Event, StrategyType

from datetime import datetime
from multiprocessing import Queue, Process


class AF:

    def __init__(self, ctp_config_path: str,
                 xtp_config_path: str,
                 enable_xtp: bool = False,
                 enable_ctp: bool = False):
        self._event_queue = Queue()
        self._strategies: list[Strategy] = list()
        self._ctp_config_path = ctp_config_path
        self._xtp_config_path = xtp_config_path
        self._end_time = 999999

        self._enable_xtp: bool = enable_xtp
        self._enable_ctp: bool = enable_ctp

    def docking(self, strategy: Strategy):
        if isinstance(strategy, Strategy):
            self._strategies.append(strategy)
        else:
            raise TypeError(f"not support strategy type: [{type(strategy)}].")

    def __on_bar(self, event: Event):
        for s in self._strategies:
            if s.type() == event.ex_type:
                s.on_bar(event.data)

    def __on_snapshot(self, event: Event):
        for s in self._strategies:
            if s.type() == event.ex_type:
                s.on_snapshot(event.data)

    def __get_symbol_codes(self, _type) -> list[str]:
        instrument_id = []

        for s in self._strategies:
            if s.type() == _type:
                instrument_id += s.sub_symbol_code

        return instrument_id

    def _start_with_normal(self):
        ctp_process = None
        xtp_process = None

        if self._enable_ctp:
            ctp_process = Process(target=ctp_start,
                                  args=(self._ctp_config_path,
                                        self._event_queue,
                                        self.__get_symbol_codes(StrategyType.CTP))
                                  )
            ctp_process.start()

        if self._enable_xtp:
            xtp_process = Process(target=xtp_start,
                                  args=(self._xtp_config_path,
                                        self._event_queue,
                                        self.__get_symbol_codes(StrategyType.XTP))
                                  )
            xtp_process.start()

        while int(datetime.now().strftime('%H%M%S')) < self._end_time:
            event: Event = self._event_queue.get()
            if not event:
                continue

            if event.event_type == EventType.SNAPSHOT_DATA:
                self.__on_snapshot(event)
            elif event.event_type == EventType.KLINE_DATA:
                self.__on_bar(event)

        if ctp_process is not None:
            ctp_process.join()
        if xtp_process is not None:
            xtp_process.terminate()

    def start(self):
        logger.info("AFramework start work")
        self._start_with_normal()
        logger.info("Framework work done.")
