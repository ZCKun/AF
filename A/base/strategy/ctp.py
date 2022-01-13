from A.types import KLine, StrategyType
from A.types.ctp import Snapshot
from .base import Strategy


class CTPStrategy(Strategy):

    def __init__(self):
        super().__init__()
        self._type = StrategyType.CTP

    def on_bar(self, bar: KLine):
        """ KLine 行情

        :param bar: kline data
        :return:
        """
        raise NotImplementedError

    def on_snapshot(self, tick: Snapshot):
        """ 快照行情

        :param tick: snapshot data
        :return:
        """
        raise NotImplementedError
