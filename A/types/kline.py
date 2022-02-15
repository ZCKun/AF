from datetime import datetime
from .base import BaseEntity

from typing import Optional


class KLine(BaseEntity):
    """ Kline 是一个K线对象 """

    def __init__(self, **value):
        if value is not None:
            self.__dict__.update(value)
        else:
            self.symbol_code: str = ''
            #: K线起点时间
            self.start_time: Optional[datetime.time] = None
            #: K线终点
            self.end_time: Optional[datetime.time] = None
            #: K线所对应的时间
            self.time: Optional[datetime.time] = None
            #: k线状态: -1 0 1
            self.style: int = 0

            #: K线起始时刻的最新价
            self.open: float = float("nan")
            #: K线时间范围内的最高价
            self.high: float = float("nan")
            #: K线时间范围内的最低价
            self.low: float = float("nan")
            #: K线结束时刻的最新价
            self.close: float = float("nan")
            #: K线时间范围内的成交量
            self.volume: int = 0
            self.turnover: float = float("nan")
            # 涨跌幅
            self.change_percent: float = float("nan")
            # #: K线起始时刻的持仓量
            # self.open_oi: int = 0
            # #: K线结束时刻的持仓量
            # self.close_oi: int = 0
