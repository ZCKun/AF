from A.types import KLine, StrategyType
from A.types.stock import Snapshot, OrderBook
from .base import Strategy


class StockStrategy(Strategy):

    def __init__(self):
        super().__init__()
        self._type = StrategyType.STOCK

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

    def on_order_book(self, orderbook: OrderBook):
        """ OrderBook 数据回调

        :param orderbook: the OrderBook data
        :return:
        """
        raise NotImplementedError

