from A.log import logger
from A.adapter import ctp_start
from A.types import EventType, Event, KLine, StrategyType
from A.types.ctp import Snapshot
from A.base.strategy import CTPStrategy

from typing import Union
from datetime import datetime
from multiprocessing import Queue, Process


class A:

    def __init__(self, ctp_config_path: str):
        self._event_queue = Queue()
        self._strategies: list[CTPStrategy] = list()
        self._ctp_config_path = ctp_config_path

    def docking(self, strategy: Union[CTPStrategy]):
        if isinstance(strategy, CTPStrategy):
            self._strategies.append(strategy)
        else:
            raise TypeError(f"not support strategy type: [{type(strategy)}].")

    def __on_bar(self, bar: KLine):
        for s in self._strategies:
            s.on_bar(bar)

    def __on_snapshot(self, tick: Snapshot):
        for s in self._strategies:
            s.on_snapshot(tick)

    def __get_ctp_sub_instrument_id(self) -> list[str]:
        instrument_id = []

        for s in self._strategies:
            if s.type() == StrategyType.CTP:
                instrument_id += s.sub_instrument_id

        return instrument_id

    def start(self):
        logger.info("AFramework start work")
        ctp_process = Process(target=ctp_start,
                              args=(self._ctp_config_path,
                                    self._event_queue,
                                    self.__get_ctp_sub_instrument_id())
                              )
        ctp_process.start()

        while int(datetime.now().strftime('%H%M%S')) < 153000:
            event: Event = self._event_queue.get()
            if not event:
                continue

            if event.event_type == EventType.SNAPSHOT_DATA:
                self.__on_snapshot(event.data)
            elif event.event_type == EventType.KLINE_DATA:
                self.__on_bar(event.data)

        ctp_process.join()

        logger.info("Framework work done.")
