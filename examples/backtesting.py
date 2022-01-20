import sys

sys.path.append("..")
from A.types import KLine

from A import AF, AFMode, Strategy, logger, StrategyType

import pandas as pd
from typing import Optional
from A.indicator import ema, calc_macd, calc_rsi, calc_sar

KDJ_WEIGHT_K = 3.0
KDJ_WEIGHT_D = 2.0


class Backtesting(Strategy):

    def __init__(self):
        super().__init__()
        self._type = StrategyType.CSV
        self.sub_symbol_code = ['399905.SZ']

        self.rsv_val = 9
        self.kval = 3
        self.dval = 3
        self.rsv_lst: list[float] = list()
        self.rsv_ema_lst: list[float] = [1]
        self.k_list: list[float] = list()
        self.k_ema_lst: list[float] = [1]
        self.low_price_lst: list[float] = list()
        self.high_price_lst: list[float] = list()

        # sar cache
        self.last_sar: float = 0
        self.last_bull: bool = True
        self.wtf_hp: float = 0
        self.wtf_lp: float = 0
        self.last_af: float = 0.02

        self.last_up_ema_lst: list[float] = [1]
        self.last_down_ema_lst: list[float] = [0]

        self.bar_df: Optional[pd.DataFrame] = None

    def kdj(
            self,
            close_price: float,
            period_rsv: int,
            period_k: int,
            period_d: int
    ) -> tuple[float, float, float]:
        """KDJ indicator

        Args:
            close_price: 仅用来计算 rsv
            period_rsv: 计算 rsv 周期
            period_k: 计算 k 值周期
            period_d: 计算 d 值周期

        Returns:
            tuple[float, float, float]: k, d, j

        """
        low_px_count = len(self.low_price_lst)
        high_px_count = len(self.high_price_lst)
        if low_px_count == 0 or high_px_count == 0:
            rsv = 0
        else:
            low_px_lst = self.low_price_lst
            high_px_lst = self.high_price_lst
            if low_px_count > period_rsv:
                low_px_lst = low_px_lst[low_px_count - period_rsv:]
            if high_px_count > period_rsv:
                high_px_lst = high_px_lst[high_px_count - period_rsv:]
            # RSV = (当日收盘价 - N日内最低价) / (N日内最高价 - N日内最低价) * 100
            min_price_of_period = min(low_px_lst)
            llv = close_price - min_price_of_period
            hhv = max(high_px_lst) - min_price_of_period
            rsv = llv / hhv * 100

        k = ema(rsv, period_k, self.rsv_ema_lst[-1])
        d = ema(k, period_d, self.k_ema_lst[-1])
        j = KDJ_WEIGHT_K * k - KDJ_WEIGHT_D * d

        self.k_list.append(k)
        self.k_ema_lst.append(d)
        self.rsv_ema_lst.append(k)
        self.rsv_lst.append(rsv)

        return k, d, j

    def test_rsi(self, bar: KLine):
        # test pass
        rsi6 = calc_rsi(self.af, 'close', 6)
        rsi12 = calc_rsi(self.af, 'close', 12)
        rsi24 = calc_rsi(self.af, 'close', 24)
        logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - RSI6:{rsi6}, RSI12:{rsi12}, RSI24:{rsi24}")

    def test_macd(self, bar: KLine):
        # test pass
        macd, dif, dea = calc_macd(bar.close, 12, 26, 9)
        logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - MACD:{macd},DIF:{dif},DEA:{dea}")

    def test_kdj(self, bar: KLine):
        k, d, j = self.kdj(bar.close,
                           period_rsv=self.rsv_val,
                           period_k=self.kval,
                           period_d=self.dval
                           )
        logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - K:{k},D:{d},J:{j}")

    def test_sar(self, bar: KLine):
        if self.wtf_hp == 0:
            self.wtf_hp = self.af.bar_data.iloc[0].high
        if self.wtf_lp == 0:
            self.wtf_lp = self.af.bar_data.iloc[0].low
        self.last_sar, self.last_af, self.last_bull, self.wtf_hp, self.wtf_lp = \
            calc_sar(
                self.af,
                self.last_sar,
                self.last_bull,
                self.wtf_hp,
                self.wtf_lp,
                self.last_af
            )
        sar_bear = None if self.last_bull else self.last_sar
        sar_bull = self.last_sar if self.last_bull else None
        logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - bear:{sar_bear}, bull:{sar_bull}")

    def on_bar(
            self,
            bar: KLine
    ) -> None:
        self.low_price_lst.append(bar.low)
        self.high_price_lst.append(bar.high)

        self.test_rsi(bar)
        self.test_macd(bar)
        self.test_kdj(bar)
        self.test_sar(bar)

    def on_snapshot(
            self,
            tick
    ) -> None:
        logger.info(tick)


def main():
    a = AF(AFMode.BACKTESTING, csv_config_path="config/csv_config.yaml", end_time=999999)
    s = Backtesting()
    a.add_strategy(s)
    a.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
