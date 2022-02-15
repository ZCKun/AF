import os.path

import pandas as pd

from A.log import logger
from A.base.strategy.base import Strategy
from A.adapter import ctp_start, xtp_start
from A.adapter.backtest import stock_start
from A.types import EventType, Event, StrategyType

from enum import Enum
from datetime import datetime
from typing import Optional
from multiprocessing import Queue, Process


class Mode(Enum):
    ONLINE = 1
    BACKTESTING = 2


class Market(Enum):
    STOCK = 1
    FUTURE = 2


class AFOptional:
    # the AF running mode.
    run_mode: Mode = None
    # the market type
    market: Market = None
    # the config path for running mode
    config_path: str = None
    # the AF work done time
    end_time: int = 0


class AF:

    def __init__(
            self,
            optional: AFOptional
    ) -> None:
        """
        AF

        Args:
            optional: AF Optional.

        Raises:
            FileNotFoundError: config file path not found/exists.
            TypeError: unknown run mode.
        """
        if optional is None:
            raise TypeError("the optional param is None.")
        self._optional: AFOptional = optional

        if self._optional.run_mode != Mode.ONLINE and self._optional.run_mode != Mode.BACKTESTING:
            raise TypeError("unknown run mode.")

        if os.path.splitext(self._optional.config_path)[-1] not in [".yaml", ".yml"]:
            raise TypeError("unsupported config file type, please use yaml type.")

        if not os.path.exists(self._optional.config_path):
            raise FileNotFoundError(f"config path {self._optional.config_path} not exists.")

        self._event_queue = Queue()
        self._strategies: list[Strategy] = list()

        self._bar_data: Optional[pd.DataFrame] = None

    @property
    def bar_data(self) -> pd.DataFrame:
        return self._bar_data

    def add_strategy(
            self,
            strategy: Strategy
    ) -> None:
        """
        append trade strategy

        Args:
            strategy: the `Strategy` instance

        Returns:
            None

        Raises:
            TypeError: unknown strategy type
        """
        if isinstance(strategy, Strategy):
            strategy.af = self
            self._strategies.append(strategy)
        else:
            raise TypeError(f"not support strategy type of [{type(strategy)}].")

    def _on_bar(
            self,
            event: Event
    ) -> None:
        """
        KLine event callback function

        Args:
            event: the event message

        Returns:
            None
        """
        for s in self._strategies:
            if s.type() == event.ex_type:
                bar = event.data
                if self._bar_data is None:
                    self._bar_data = pd.DataFrame([bar])
                else:
                    self._bar_data = self._bar_data.append(bar.__dict__, ignore_index=True, sort=False)
                s.on_bar(bar)

    def _on_snapshot(
            self,
            event: Event
    ) -> None:
        """
        Snapshot event callback function

        Args:
            event: the event message

        Returns:
            None
        """
        for s in self._strategies:
            if s.type() == event.ex_type:
                s.on_snapshot(event.data)

    def _get_symbol_codes(
            self,
            _type
    ) -> list[str]:
        """
        get the symbol code from strategies

        Args:
            _type:

        Returns:
            list[str]: the symbol code list
        """
        instrument_id = []

        for s in self._strategies:
            if s.type() == _type:
                instrument_id += s.sub_symbol_code

        return instrument_id

    def _on_event(
            self,
            event: Event
    ) -> None:
        """
        on event callback function

        Args:
            event: the event message

        Returns:
            None
        """
        if event.event_type == EventType.SNAPSHOT_DATA:
            self._on_snapshot(event)
        elif event.event_type == EventType.KLINE_DATA:
            self._on_bar(event)

    def _start_with_online(self) -> None:
        start_func = None
        if self._optional.market == Market.STOCK:
            start_func = xtp_start
        elif self._optional.market == Market.FUTURE:
            start_func = ctp_start

        process = Process(target=start_func,
                          args=(self._optional.config_path,
                                self._event_queue,
                                self._get_symbol_codes(StrategyType.FUTURES))
                          )
        process.start()

        while int(datetime.now().strftime('%H%M%S')) < self._optional.end_time:
            event: Event = self._event_queue.get()
            if not event:
                continue
            self._on_event(event)

        if self._optional.market == Market.STOCK:
            process.terminate()
        else:
            process.join()

    def _start_with_backtesting(self) -> None:
        start_func = None
        if self._optional.market == Market.STOCK:
            start_func = stock_start

        start_func(self._optional.config_path,
                   self._event_queue,
                   self._get_symbol_codes(StrategyType.STOCK))
        process = Process(target=start_func,
                          args=(self._optional.config_path,
                                self._event_queue,
                                self._get_symbol_codes(StrategyType.STOCK))
                          )
        process.start()

        while int(datetime.now().strftime('%H%M%S')) < self._optional.end_time:
            event: Event = self._event_queue.get()
            if not event:
                continue
            self._on_event(event)

        process.join()

    def start(self) -> None:
        logger.info("AFramework start work")

        if self._optional.run_mode == Mode.ONLINE:
            self._start_with_online()
        elif self._optional.run_mode == Mode.BACKTESTING:
            self._start_with_backtesting()

        logger.info("Framework work done.")
