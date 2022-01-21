import sys

sys.path.append("..")
from A.types import KLine, BuySell

from A import AF, AFMode, Strategy, logger, StrategyType

from typing import Optional
from A.indicator import sma, ema, calc_macd, calc_rsi, calc_sar

KDJ_WEIGHT_K = 3.0
KDJ_WEIGHT_D = 2.0


class Backtesting(Strategy):
    """Volume breakout MA Strategy"""

    def __init__(self):
        super().__init__()
        self._type = StrategyType.CSV
        self.sub_symbol_code = ['IF9999']

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

        # strategy variables
        self._indicator_data: dict = dict(
            kdj=dict(
                k=0.,
                d=0.,
                j=0.,
            ),
            macd=dict(
                macd=0.,
                dif=0.,
                dea=0.,
            ),
            rsi=dict(
                rsi1=0.,
                rsi2=0.,
                rsi3=0.,
            ),
            sar=dict(
                bear=0.,
                bull=0.
            )
        )
        self._is_vol_break: bool = False
        # 放量时 bar 的颜色, -1绿 1红 0无
        self._vol_break_bar_base: int = 0
        # 放量期间最高价的 bar
        self._high_bar_on_break_time: Optional[KLine] = None
        self._last_macd: float = 0.
        self._last_dif: float = 0.

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

    def _calc_rsi(self, bar: KLine):
        # test pass
        rsi6 = calc_rsi(self.af, 'close', 6)
        rsi12 = calc_rsi(self.af, 'close', 12)
        rsi24 = calc_rsi(self.af, 'close', 24)

        rsi_ref = self._indicator_data['rsi']
        rsi_ref['rsi1'] = rsi6
        rsi_ref['rsi2'] = rsi12
        rsi_ref['rsi3'] = rsi24
        # logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - RSI6:{rsi6}, RSI12:{rsi12}, RSI24:{rsi24}")

    def _calc_macd(self, bar: KLine):
        # test pass
        macd, dif, dea = calc_macd(bar.close, 12, 26, 9)

        macd_ref = self._indicator_data['macd']
        macd_ref['macd'] = macd
        macd_ref['dif'] = dif
        macd_ref['dea'] = dea
        # logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - MACD:{macd},DIF:{dif},DEA:{dea}")

    def _calc_kdj(self, bar: KLine):
        k, d, j = self.kdj(bar.close,
                           period_rsv=self.rsv_val,
                           period_k=self.kval,
                           period_d=self.dval
                           )

        kdj_ref = self._indicator_data['kdj']
        kdj_ref['k'] = k
        kdj_ref['d'] = d
        kdj_ref['j'] = j
        # logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - K:{k},D:{d},J:{j}")

    def _calc_sar(self, bar: KLine):
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

        sar_ref = self._indicator_data['sar']
        sar_ref['bear'] = sar_bear
        sar_ref['bull'] = sar_bull
        # logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - bear:{sar_bear}, bull:{sar_bull}")

    def _macd_vote(self) -> tuple[int, int]:
        """
        MACD vote

        Returns:
            tuple[int, int]: buy weight, sell weight

        """
        macd_ref = self._indicator_data['macd']
        macd = macd_ref['macd']
        dif = macd_ref['dif']

        buy_count = 0
        sell_count = 0
        if self._last_macd != 0:
            if macd > self._last_macd:
                buy_count += 1
            elif macd < self._last_macd:
                sell_count += 1

        if self._last_dif != 0:
            if dif > self._last_dif:
                buy_count += 1
            elif dif < self._last_dif:
                sell_count += 1

        self._last_macd = macd
        self._last_dif = dif

        return buy_count, sell_count

    def _rsi_vote(self) -> tuple[int, int]:
        """
        RSI vote

        Returns:
            tuple[int, int]: buy weight, sell weight

        """
        rsi_ref = self._indicator_data['rsi']
        rsi6 = rsi_ref['rsi1']
        rsi12 = rsi_ref['rsi2']
        rsi24 = rsi_ref['rsi3']

        buy_count = 0
        sell_count = 0
        if rsi6 > rsi12 or rsi6 > rsi24:
            buy_count += 1
        elif rsi6 < rsi24 or rsi6 < rsi12:
            sell_count += 1

        if rsi12 > rsi24:
            buy_count += 1
        elif rsi12 < rsi24:
            sell_count += 1

        return buy_count, sell_count

    def _kdj_vote(self) -> tuple[int, int]:
        """
        KDJ vote

        Returns:
            tuple[int, int]: buy weight, sell weight

        """
        kdj = self._indicator_data['kdj']
        k = kdj['k']
        d = kdj['d']

        if k > d:
            return 1, 0
        if d > k:
            return 0, 1

    def _sar_vote(self) -> tuple[int, int]:
        """
        SAR vote

        Returns:
            tuple[int, int]: buy weight, sell weight

        """
        sar_ref = self._indicator_data['sar']
        sar_bear = sar_ref['bear']
        sar_bull = sar_ref['bull']

        bull = 0 if sar_bull is None else 1
        bear = 0 if sar_bear is None else 1

        return bear, bull

    def indicator_vote(
            self,
            bs: BuySell
    ) -> bool:
        buy_weight = 0
        sell_weight = 0

        l = [self._macd_vote(), self._rsi_vote(), self._kdj_vote(), self._sar_vote()]
        for buy_count, sell_count in [self._sar_vote()]:
            buy_weight += buy_count
            sell_weight += sell_count

        if bs == BuySell.Buy:
            return buy_weight > sell_weight
        return sell_weight > buy_weight

    def is_vol_break(
            self,
            bar: KLine
    ) -> bool:
        """
        放量判断
        计算 volume 的 MA 3, 6, 12. 当前 volume 突破这三条 MA 时放量

        Args:
            bar: 当前 KLine

        Returns:
            bool: 是否放量

        """
        history_vols = self.af.bar_data['volume']
        vol_ma1 = sma(3, history_vols)
        vol_ma2 = sma(6, history_vols)
        vol_ma3 = sma(12, history_vols)

        return (bar.volume > vol_ma1) and \
               (bar.volume > vol_ma2) and \
               (bar.volume > vol_ma3)

    def on_bar(
            self,
            bar: KLine
    ) -> None:
        self.low_price_lst.append(bar.low)
        self.high_price_lst.append(bar.high)
        self._calc_macd(bar)
        self._calc_kdj(bar)
        self._calc_rsi(bar)
        self._calc_sar(bar)

        if self.is_vol_break(bar):
            self._vol_break_bar_base = bar.style
            self._is_vol_break = True

        if self._is_vol_break:
            if self._high_bar_on_break_time is None or bar.high > self._high_bar_on_break_time.high:
                self._high_bar_on_break_time = bar

            # 反转
            if bar.style != self._vol_break_bar_base:
                diff = abs(bar.change_percent - self._high_bar_on_break_time.change_percent)
                # 抵消
                if diff >= 0:
                    # 投票表决
                    bs = BuySell.Buy if self._vol_break_bar_base == 1 else BuySell.Sell
                    if self.indicator_vote(bs):
                        logger.info(
                            f"[{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}]下单 {'BUY' if bs == BuySell.Buy else 'SELL'}, Price:{bar.close}")

        if bar.datetime.hour == 15:
            logger.debug(f"[{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}]")

        # self.test_rsi(bar)
        # self.test_macd(bar)
        # self.test_kdj(bar)
        # self.test_sar(bar)

    def on_snapshot(
            self,
            tick
    ) -> None:
        logger.info(tick)


def main():
    a = AF(
        AFMode.BACKTESTING,
        csv_config_path="config/csv_config.yaml",
        end_time=999999
    )
    a.add_strategy(Backtesting())
    a.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
