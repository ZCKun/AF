import sys

sys.path.append("..")
from A.types import KLine

from A import AF, AFMode, Strategy, logger, StrategyType

import numpy as np
import pandas as pd
import talib as ta
from typing import Optional


def sma(
        n: int,
        price_lst: list[float]
) -> float:
    if (size := len(price_lst)) < n:
        return 0
    prices = price_lst[size - n:]
    return sum(prices) / n


def ewma(
        array: np.ndarray,
        period: int,
        init: float
):
    """Exponentially weighted moving average
    https://en.wikipedia.org/wiki/Moving_average#Exponential_moving_average
    with
    - init value as `50.0`
    - alpha as `1 / period`
    """

    # If there is no value k or value d of the previous day,
    # then use 50.0
    k = init
    alpha = 1. / period
    base = 1 - alpha

    for i in array:
        k = base * k + alpha * i
        yield k


def ema(
        price: float,
        period: int,
        last_ema: float,
        span: bool = True
) -> float:
    """
    Calculate exponential weighted (EW).

    Args:
        price: target price
        period: Specify decay in terms
        last_ema: before ema value
        span: Specify decay in terms of span. if true, alpha = 2 / (period + 1)

    Returns:
        float: ema value

    """
    alpha = 2. / (period + 1) if span else 1. / period
    base = 1 - alpha
    return last_ema * base + alpha * price


KDJ_WEIGHT_K = 3.0
KDJ_WEIGHT_D = 2.0


class Backtesting(Strategy):

    def __init__(self):
        super().__init__()
        self._type = StrategyType.CSV
        self.sub_symbol_code = ['399905.SZ']

        self.price_lst: list[float] = list()
        self.dif_list: list[float] = [0]
        self.ema1_lst: list[float] = [1]
        self.ema2_lst: list[float] = [1]
        self.dif_ema_lst: list[float] = [1]

        self.rsv_val = 9
        self.kval = 3
        self.dval = 3
        self.rsv_lst: list[float] = list()
        self.rsv_ema_lst: list[float] = [1]
        self.k_list: list[float] = list()
        self.k_ema_lst: list[float] = [1]
        self.low_price_lst: list[float] = list()
        self.high_price_lst: list[float] = list()

        self.last_sar: float = 0
        self.last_bull: bool = True
        self.wtf_hp: float = 0
        self.wtf_lp: float = 0
        self.last_af: float = 0.02

        self.last_up_ema_lst: list[float] = [1]
        self.last_down_ema_lst: list[float] = [0]

        self.bar_df: Optional[pd.DataFrame] = None

    def dif(
            self,
            price: float,
            period_s: int,
            period_l: int
    ) -> float:
        """
        DIF
        the price of short period ema - the price of long period ema

        Args:
            price:
            period_s:
            period_l:

        Returns:
            float: dif value

        """
        ma1 = ema(price, period_s, self.ema1_lst[-1])
        ma2 = ema(price, period_l, self.ema2_lst[-1])
        self.ema1_lst.append(ma1)
        self.ema2_lst.append(ma2)

        dif = ma1 - ma2
        return dif

    def dea(
            self,
            period: int,
            dif: float
    ) -> float:
        """
        DEA

        Args:
            period: period
            dif:

        Returns:
            float: dea value

        """
        dif_ema = ema(dif, period, self.dif_ema_lst[-1])
        dea = dif_ema  # / close_price
        self.dif_ema_lst.append(dif_ema)
        return dea

    def macd(
            self,
            price: float,
            period_s: int,
            period_l: int,
            period_m: int
    ) -> tuple[float, float, float]:
        """MACD indicator

        有些小问题

        Args:
            price:
            period_s: the period of DIFF short
            period_l: the period of DIFF long
            period_m: the period of DEA

        Returns:
            tuple[float, float, float]: macd, dif, dea

        """
        dif = self.dif(price, period_s, period_l)
        dea = self.dea(period_m, dif)
        macd = 2 * (dif - dea)
        self.dif_list.append(dif)
        return macd, dif, dea

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

    def sar(
            self,
            last_sar: float,
            bull: bool,
            wtf_high_price: float = 0,
            wtf_low_price: float = 0,
            af: Optional[float] = 0.02,
            base_af: Optional[float] = 0.02,
            max_af: Optional[float] = 0.2
    ) -> tuple[float, float, float, float, float]:
        """
        SAR indicator

        Args:
            last_sar: 历史 SAR
            bull: 历史 bull
            wtf_high_price: some high price?
            wtf_low_price: some low price?
            af: 历史 AF
            base_af: 基础值 AF
            max_af: 最大 AF

        Returns:
            tuple[float, float, float, float, float]: sar, af, bull, wtf_high_price, wtf_low_price

        """
        if len(self.bar_df) == 0:
            return 0, af, bull, wtf_high_price, wtf_low_price
        elif len(self.bar_df) < 3:
            return self.bar_df.iloc[-1].close, af, bull, wtf_high_price, wtf_low_price

        bar = self.bar_df.iloc[-1]
        last_bar = self.bar_df.iloc[-2]
        high_price = bar.high
        low_price = bar.low
        last_high_price = last_bar.high
        last_low_price = last_bar.low

        reverse = False
        if bull:
            sar = last_sar + af * (wtf_high_price - last_sar)
        else:
            sar = last_sar + af * (wtf_low_price - last_sar)
        if bull:
            if low_price < sar:
                bull = False
                reverse = True
                sar = wtf_high_price
                wtf_low_price = low_price
                af = base_af
        else:
            if high_price > sar:
                bull = True
                reverse = True
                sar = wtf_low_price
                wtf_high_price = high_price
                af = base_af

        if not reverse:
            if bull:
                if high_price > wtf_high_price:
                    wtf_high_price = high_price
                    af = min(af + base_af, max_af)
                if last_low_price < sar:
                    sar = last_low_price
                if last_bar.low < sar:
                    sar = last_bar.low
            else:
                if low_price < wtf_low_price:
                    wtf_low_price = low_price
                    af = min(af + base_af, max_af)
                if last_high_price > sar:
                    sar = last_high_price
                if last_bar.high > sar:
                    sar = last_bar.high

        return sar, af, bull, wtf_high_price, wtf_low_price

    def rsi(
            self,
            base: str,
            period: int
    ) -> float:
        l = len(self.af.bar_data)
        if l < period:
            return 0
        return ta.RSI(self.af.bar_data[base], period).iloc[-1]

    def _rsi(
            self,
            base: float,
            last: float,
            period: int,
            last_up_ema: float,
            last_down_ema: float
    ) -> tuple[float, float, float]:
        """
        RSI indicator

        Args:
            base: 当前价格
            last: 历史价格
            period: 区间
            last_up_ema: 历史 up ema
            last_down_ema: 历史 down ema

        Returns:
            tuple[float, float, float]: rsi, up ema, down ema

        """
        if len(self.bar_df) <= period:
            return 0, last_up_ema, last_down_ema

        diff = base - last
        up = 0
        down = 0
        # 上涨 or 下跌
        if diff > 0:
            up = diff
        else:
            down = abs(diff)
        # 计算各自的 ema
        up_ema = ema(up, period, last_up_ema)
        down_ema = ema(down, period, last_down_ema)
        # 计算 rsi
        rs = 0
        if down_ema != 0:
            rs = up_ema / down_ema
        rsi = 100 - 100 / (1 + rs)
        return rsi, up_ema, down_ema

    def test_rsi(self, bar: KLine):
        rsi6 = self.rsi('close', 6)
        rsi12 = self.rsi('close', 12)
        rsi24 = self.rsi('close', 24)
        logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - RSI6:{rsi6}, RSI12:{rsi12}, RSI24:{rsi24}")

    def test_macd(self, bar: KLine):
        macd, dif, dea = self.macd(bar.close, 12, 26, 9)
        if bar.datetime.year > 2018:
            logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - MACD:{macd},DIF:{dif},DEA:{dea},"
                         f"ma12:{self.ema1_lst[-1]},ma26:{self.ema2_lst[-1]}")

    def test_kdj(self, bar: KLine):
        k, d, j = self.kdj(bar.close,
                           period_rsv=self.rsv_val,
                           period_k=self.kval,
                           period_d=self.dval
                           )
        logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - K:{k},D:{d},J:{j}")

    def test_sar(self, bar: KLine):
        if self.wtf_hp == 0:
            self.wtf_hp = self.bar_df.iloc[0].high
        if self.wtf_lp == 0:
            self.wtf_lp = self.bar_df.iloc[0].low
        self.last_sar, self.last_af, self.last_bull, self.wtf_hp, self.wtf_lp = \
            self.sar(
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
        # if self.bar_df is None:
        #     self.bar_df = pd.DataFrame([bar])
        # else:
        #     self.bar_df = self.bar_df.append(bar.__dict__, ignore_index=True, sort=False)

        close_price = bar.close
        self.price_lst.append(close_price)
        self.low_price_lst.append(bar.low)
        self.high_price_lst.append(bar.high)

        self.test_rsi(bar)
        # self.test_macd(bar)
        # self.test_kdj(bar)
        # self.test_sar(bar)

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
