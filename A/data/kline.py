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
        start.replace(year=replace_date.year, month=replace_date.month, day=replace_date.day)

    i = int(start.strftime('%H%M%S'))
    weekday = datetime.weekday(datetime.today())
    if weekday in [5, 6] or not 93000 < i < 150000:
        start = datetime.strptime('93000', '%H%M%S')

    end = datetime.strptime('150000', '%H%M%S')
    ret = []

    while True:
        # 跳过休盘时间段
        start += timedelta(seconds=interval)
        if start.time() > end.time():
            break
        if not (113000 < int(start.strftime('%H%M%S')) < 130100):
            ret.append(start)

    return ret


def create_kline(symbol_code: str, open_price: float, close_price: float, high_price: float, low_price: float,
                 volume: int, start_date: int, end_date: int, _date, style: Optional[int] = 0) -> KLine:
    """创建Kline对象

    Args:
        symbol_code: 标的代码
        open_price: 开盘价
        close_price: 收盘价
        high_price: 最高价
        low_price:  最低价
        volume: 成交量
        start_date: 开始时间
        end_date: 结束时间
        _date: 当前Kline所指的时间
        style: Kline样式; 0: 收盘价等于开盘价, 1: 阳线, -1: 阴线
    Returns: K线对象
    """
    obj = KLine()
    obj.datetime = _date
    obj.symbol_code = symbol_code
    obj.close = close_price
    obj.open = open_price
    obj.high = high_price
    obj.low = low_price
    obj.volume = volume

    obj.start_datetime = start_date
    obj.end_datetime = end_date
    obj.time = int(_date.strftime("%H%M%S"))
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
        self._t0_date: datetime = t0_date
        self._interval = interval

        self._quote_cache = []
        self._callbacks = []
        # self._yesterday_date = (datetime.today() - timedelta(days=10)).strftime('%Y%m%d')

        self.quotes = []
        self.kline_lst = []

        self._period = generator_period_dt(self._interval, self._t0_date)

    def subscribe(self, callback):
        self._callbacks.append(callback)

    def _is_end(self):
        if len(self._quote_cache) >= 3:
            try:
                current_last_modified_full = self._quote_cache[-1].last_modified_full.iloc[0]
            except AttributeError:
                current_last_modified_full = self._quote_cache[-1].last_modified_full

            if current_last_modified_full >= self._period[0].time():
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

        last_price_series: Series = quote_cache_df.last_price.astype(float)
        last_modified_full = quote_cache_df.last_modified_full

        open_price = last_price_series.iloc[0]
        close_price = last_price_series.iloc[-2]

        high_price = last_price_series.max()
        low_price = last_price_series.min()

        start_date = last_modified_full.iloc[0]
        end_date = last_modified_full.iloc[-2]

        if open_price > close_price:
            style = -1
        elif open_price < close_price:
            style = 1
        else:
            style = 0

        kline = create_kline(
            symbol_code=self._symbol_code,
            open_price=open_price,
            close_price=close_price,
            high_price=high_price,
            low_price=low_price,
            volume=0,
            start_date=start_date,
            end_date=end_date,
            style=style,
            # _date=kline_date)
            _date=self._kline_date)

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
