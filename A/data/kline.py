import pandas as pd

from pandas import Series
from typing import List, Optional
from datetime import timedelta, datetime
from A.types.kline import KLine


def generator_period_dt(interval: int,
                        start_dt: datetime = None,
                        replace_date: Optional[datetime] = None) -> List[datetime]:
    if start_dt is None:
        start = datetime.strptime("93000", "%H%M%S")
    else:
        start = start_dt

    if replace_date is not None:
        start = start.replace(year=replace_date.year, month=replace_date.month, day=replace_date.day)

    i = int(start.strftime('%H%M%S'))
    if i < 9_30_00 or i > 15_00_00:
        start = datetime.strptime('93000', '%H%M%S')

    end = datetime.strptime('150000', '%H%M%S')
    ret = []

    while True:
        # 跳过休盘时间段
        start += timedelta(seconds=interval)
        if start.time() > end.time():
            break
        if not (113000 < int(start.strftime('%H%M%S')) < 130100):
            ret.append(start.replace(second=0, microsecond=0))

    return ret


def create_kline(
        symbol_code: str,
        open_price: float,
        close_price: float,
        high_price: float,
        low_price: float,
        volume: int,
        change_percent: float,
        start_time: int,
        end_time: int,
        time: datetime.time,
        style: Optional[int] = 0
) -> KLine:
    """创建Kline对象

    Args:
        change_percent: 涨跌幅
        symbol_code: 标的代码
        open_price: 开盘价
        close_price: 收盘价
        high_price: 最高价
        low_price:  最低价
        volume: 成交量
        start_time: 开始时间
        end_time: 结束时间
        time: 当前Kline所指的时间
        style: Kline样式; 0: 收盘价等于开盘价, 1: 阳线, -1: 阴线
    Returns: K线对象
    """
    obj = KLine()
    obj.time = time
    obj.symbol_code = symbol_code
    obj.close = close_price
    obj.open = open_price
    obj.high = high_price
    obj.low = low_price
    obj.volume = volume
    obj.change_percent = change_percent

    obj.start_time = start_time
    obj.end_time = end_time
    obj.style = style

    return obj


class KLineHandle:

    def __init__(
            self,
            symbol_code: str,
            interval: int = 60,
            t0_date: Optional[datetime] = None
    ):
        self._symbol_code = symbol_code
        if t0_date is None:
            t0_date = datetime.today()
        self._t0_date: datetime = t0_date
        self._interval = interval

        self._quote_cache = []
        self._callbacks = []

        self.quotes = []
        self.kline_lst: list[KLine] = []

        self._period = generator_period_dt(self._interval, replace_date=self._t0_date)

    def subscribe(self, callback):
        self._callbacks.append(callback)

    def _is_end(self):
        if len(self._quote_cache) >= 3:
            try:
                current_last_modified_full = self._quote_cache[-1]['data_time'].iloc[0]
            except AttributeError:
                current_last_modified_full = self._quote_cache[-1]['data_time']

            if current_last_modified_full.time() >= self._period[0].time():
                self._kline_date = self._period[0]
                del self._period[0]
                return True

        return False

    def _save_quote(self, quote: Series):
        """
        每来一条行情就保存
        Args:
            quote (:py:class:`~pandas.Series`): 最新行情消息
        Returns:
        """
        self.quotes.append(quote)
        self._quote_cache.append(quote)

    def _make_kline(self) -> KLine:
        """ 创建一根k线 """
        quote_cache_df = pd.concat(self._quote_cache)

        last_price_series: Series = quote_cache_df['last_price']
        data_time_series: Series = quote_cache_df['data_time']

        open_price = last_price_series.iloc[0]
        close_price = last_price_series.iloc[-2]

        high_price = last_price_series.max()
        low_price = last_price_series.min()

        start_date = data_time_series.iloc[0]
        end_date = data_time_series.iloc[-2]

        volume_s = quote_cache_df['volume']
        volume = volume_s.sum()

        if open_price > close_price:
            style = -1
        elif open_price < close_price:
            style = 1
        else:
            style = 0

        change_percent = .0
        if len(self.kline_lst) > 0 and (last_close_price := self.kline_lst[-1].close) != 0:
            change_percent = ((close_price / last_close_price) - 1) * 100

        kline = create_kline(
            symbol_code=self._symbol_code,
            open_price=open_price,
            close_price=close_price,
            high_price=high_price,
            low_price=low_price,
            volume=volume,
            change_percent=change_percent,
            start_time=start_date.time(),
            end_time=end_date.time(),
            style=style,
            time=self._kline_date.time(),
        )

        self.kline_lst.append(kline)

        return kline

    @property
    def bars(self):
        return self.kline_lst

    def do(self, message: pd.Series):
        if len(self._period) <= 0:
            self._period = generator_period_dt(self._interval, self._t0_date)

        self._save_quote(message)

        if self._is_end():
            bar = self._make_kline()
            for cb in self._callbacks:
                cb(bar)
            self._cache_clean()

    def _cache_clean(self):
        # if int(self._quote_cache[0].last_modified_full.strftime('%H%M')) != 1300:
        # 每一分钟清理一次行情缓存，因为缓存中保存了一下分钟的第一条行情，所以保留最后一条缓存
        del self._quote_cache[:-1]
