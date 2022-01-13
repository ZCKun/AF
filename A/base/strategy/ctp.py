from A.types import KLine, StrategyType
from A.types.ctp import Snapshot


class CTPStrategy:

    def __init__(self):
        self._type = StrategyType.CTP
        self._sub_instrument_id: list[str] = list()

    @property
    def sub_instrument_id(self) -> list[str]:
        return self._sub_instrument_id

    def type(self):
        return self._type

    @sub_instrument_id.setter
    def sub_instrument_id(self, instrument: list[str]):
        self._sub_instrument_id = instrument

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
