import sys

sys.path.append("..")
from A.types import KLine

from A import AF, AFMode, Strategy, logger, StrategyType

from typing import Optional, Union


def sma(
        n: int,
        price_lst: list[float]
) -> float:
    if (size := len(price_lst)) < n:
        return 0
    prices = price_lst[size - n:]
    return sum(prices) / n


def ema(
        price_lst: list[float],
        n: int,
        smoothing: int = 2,
        ema_lst: list[float] = None
) -> float:
    if (size := len(price_lst)) < n:
        return 0

    if not ema_lst:
        ema = sum(price_lst[size - n:]) / n
        return ema

    val = smoothing / (1 + n)
    l = price_lst[-1] * val
    r = ema_lst[-1] * (1 - val)
    return l + r


KDJ_WEIGHT_K = 3.0
KDJ_WEIGHT_D = 2.0


class Backtesting(Strategy):

    def __init__(self):
        super().__init__()
        self._type = StrategyType.CSV
        self.sub_symbol_code = ['399905.SZ']

        self.price_lst: list[float] = list()
        self.dif_list: list[float] = list()
        self.ema1_lst: list[float] = list()
        self.ema2_lst: list[float] = list()
        self.dif_ema_lst: list[float] = list()

        self.kval = 9
        self.dval = 3
        self.jval = 3
        self.rsv_lst: list[float] = list()
        self.rsv_ema_lst: list[float] = list()
        self.k_list: list[float] = list()
        self.k_ema_lst: list[float] = list()
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
            close_price: float
    ) -> float:
        """
        DIF

        Args:
            close_price:

        Returns:
            float: dif value

        """
        ma1 = ema(self.price_lst, 12, ema_lst=self.ema1_lst)
        ma2 = ema(self.price_lst, 26, ema_lst=self.ema2_lst)
        self.ema1_lst.append(ma1)
        self.ema2_lst.append(ma2)

        dif = (ma1 - ma2) / close_price
        return dif

    def dea(
            self,
            n: int,
            close_price: float
    ) -> float:
        """
        DEA

        Args:
            n: period
            close_price:

        Returns:
            float: dea value

        """
        if len(self.dif_list) < n:
            return 0
        dif_ema = ema(self.dif_list, n, ema_lst=self.dif_ema_lst)
        dea = dif_ema / close_price
        self.dif_ema_lst.append(dif_ema)
        return dea

    def macd(
            self,
            price
    ) -> tuple[float, float, float]:
        """MACD指标

        Args:
            price:

        Returns:
            tuple[float, float, float]: macd, dif, dea

        """
        dif = self.dif(price)
        dea = self.dea(9, price)
        macd = 2 * (dif - dea)
        self.dif_list.append(dif)
        return macd, dif, dea

    def kdj(
            self,
            close_price: float,
            period_k: int,
            period_d: int,
            period_rsv: int
    ) -> tuple[float, float, float]:
        """KDJ指标

        Args:
            close_price: 仅用来计算 rsv
            period_k: 计算 k 值周期
            period_d: 计算 d 值周期
            period_rsv: 计算 rsv 周期

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

        k = ema(self.rsv_lst, period_k, ema_lst=self.rsv_ema_lst)
        d = ema(self.k_list, period_d, ema_lst=self.k_ema_lst)
        j = KDJ_WEIGHT_K * k - KDJ_WEIGHT_D * d

        self.k_list.append(k)
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
        if self.wtf_hp == 0:
            self.wtf_hp = self.bar_data_lst[0].high
        if self.wtf_lp == 0:
            self.wtf_lp = self.bar_data_lst[0].low
        # macd, dif, dea = self.macd(close_price)
        # if bar.datetime.year > 2018:
        #     logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - MACD:{macd}, DIF:{dif}, DEA:{dea}, "
        #                  f"ma12:{self.ema1_lst[-1]}, ma26:{self.ema2_lst[-1]}")
        # k, d, j = self.kdj(close_price,
        #                    period_k=self.kval,
        #                    period_d=self.dval,
        #                    period_rsv=self.kval)
        # logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - K:{k}, D:{d}, J:{j}")
        # self.price_lst.append(close_price)
        # self.low_price_lst.append(bar.low)
        # self.high_price_lst.append(bar.high)

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
