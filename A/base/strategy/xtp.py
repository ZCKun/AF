from A.types import KLine, StrategyType
from A.types.xtp import Snapshot
from .base import Strategy


class XTPStrategy(Strategy):

    def __init__(self):
        super().__init__()
        self._type = StrategyType.XTP

    def on_bar(self, bar: KLine):
        """ KLine 数据回调

        :param bar: the kline data
        :return:
        """
        raise NotImplementedError

    def on_snapshot(self, tick: Snapshot):
        """ 行情快照数据回调

        :param tick: the snapshot data
        :return:
        """
        raise NotImplementedError
