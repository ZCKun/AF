import sys
import time

sys.path.append("..")
from A.types import KLine

from A import AF, AFMode, Strategy, logger, StrategyType

from typing import Optional
import numpy as np
import pandas as pd


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
        last_ema: float
) -> float:
    alpha = 1. / period
    base = 1 - alpha
    return last_ema * base + alpha * price


def smma(
        array: np.ndarray,
        period: int
) -> np.ndarray:
    ema(array.astype(float), period, )


KDJ_WEIGHT_K = 3.0
KDJ_WEIGHT_D = 2.0


class Backtesting(Strategy):

    def __init__(self):
        super().__init__()
        self._type = StrategyType.CSV
        self.sub_symbol_code = ['399905.SZ']

        self.price_lst: list[float] = list()
        self.dif_list: list[float] = [0]
        self.ema1_lst: list[float] = [0]
        self.ema2_lst: list[float] = [0]
        self.dif_ema_lst: list[float] = [0]

        self.rsv_val = 9
        self.kval = 3
        self.dval = 3
        self.rsv_lst: list[float] = list()
        self.rsv_ema_lst: list[float] = [0]
        self.k_list: list[float] = list()
        self.k_ema_lst: list[float] = [0]
        self.low_price_lst: list[float] = list()
        self.high_price_lst: list[float] = list()

        self.bar_data_lst: list[KLine] = list()
        self.last_sar: float = 0
        self.last_bull: bool = True
        self.wtf_hp: float = 0
        self.wtf_lp: float = 0
        self.last_af: float = 0.02

    def dif(
            self,
            price: float,
            period_s: int,
            period_l: int
    ) -> float:
        """
        DIF

        Args:
            price:
            period_s:
            period_l:

        Returns:
            float: dif value

        """
        ma1 = ema(price, period_s, self.ema1_lst[-1])
        # ma1 = ema(self.price_lst, 12, ema_lst=self.ema1_lst)
        ma2 = ema(price, period_l, self.ema2_lst[-1])
        # ma2 = ema(self.price_lst, 26, ema_lst=self.ema2_lst)
        self.ema1_lst.append(ma1)
        self.ema2_lst.append(ma2)

        dif = (ma1 - ma2)  # / close_price
        return dif

    def dea(
            self,
            period: int,
            close_price: float,
            dif: float
    ) -> float:
        """
        DEA

        Args:
            period: period
            close_price:
            dif:

        Returns:
            float: dea value

        """
        # if len(self.dif_list) < n:
        #     return 0
        dif_ema = ema(dif, period, self.dif_ema_lst[-1])
        # dif_ema = ema(self.dif_list, n, ema_lst=self.dif_ema_lst)
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
        """MACD指标

        Args:
            price:
            period_s:
            period_l:
            period_m:

        Returns:
            tuple[float, float, float]: macd, dif, dea

        """
        dif = self.dif(price, period_s, period_l)
        dea = self.dea(period_m, price, dif)
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
        """KDJ指标

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
    ) -> tuple:
        if len(self.bar_data_lst) == 0:
            return 0, af, bull, wtf_high_price, wtf_low_price
        elif len(self.bar_data_lst) < 3:
            return self.bar_data_lst[-1].close, af, bull, wtf_high_price, wtf_low_price

        bar = self.bar_data_lst[-1]
        last_bar = self.bar_data_lst[-2]
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
                if self.bar_data_lst[-2].low < sar:
                    sar = self.bar_data_lst[-2].low
            else:
                if low_price < wtf_low_price:
                    wtf_low_price = low_price
                    af = min(af + base_af, max_af)
                if last_high_price > sar:
                    sar = last_high_price
                if self.bar_data_lst[-2].high > sar:
                    sar = self.bar_data_lst[-2].high

        return sar, af, bull, wtf_high_price, wtf_low_price

    def on_bar(
            self,
            bar: KLine
    ) -> None:
        self.bar_data_lst.append(bar)
        close_price = bar.close
        self.price_lst.append(close_price)
        self.low_price_lst.append(bar.low)
        self.high_price_lst.append(bar.high)

        macd, dif, dea = self.macd(close_price, 12, 26, 9)
        if bar.datetime.year > 2018:
            logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - MACD:{macd}, DIF:{dif}, DEA:{dea}, "
                         f"ma12:{self.ema1_lst[-1]}, ma26:{self.ema2_lst[-1]}")

        # k, d, j = self.kdj(close_price,
        #                    period_rsv=self.rsv_val,
        #                    period_k=self.kval,
        #                    period_d=self.dval
        #                    )
        # logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - K:{k},D:{d},J:{j}")

        # if self.wtf_hp == 0:
        #     self.wtf_hp = self.bar_data_lst[0].high
        # if self.wtf_lp == 0:
        #     self.wtf_lp = self.bar_data_lst[0].low
        # self.last_sar, self.last_af, self.last_bull, self.wtf_hp, self.wtf_lp = \
        #     self.sar(
        #         self.last_sar,
        #         self.last_bull,
        #         self.wtf_hp,
        #         self.wtf_lp,
        #         self.last_af
        #     )
        # sar_bear = None if self.last_bull else self.last_sar
        # sar_bull = self.last_sar if self.last_bull else None
        # logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - bear:{sar_bear}, bull:{sar_bull}")

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
