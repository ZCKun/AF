import talib as ta
import functools

from A import AF
from .base import ema
from typing import Optional, Any


class T:
    """ just for cache """
    @staticmethod
    def cache(
            param_name: Optional[str] = None,
            param: Optional[Any] = None
    ):
        """
        cache variables, currently only one variable is supported. :p

        Args:
            param_name: variable name
            param: variables in variable

        Returns:
            wrapper

        """
        def _cache(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                kwargs[param_name] = param
                return func(*args, **kwargs)

            return wrapper

        return _cache


def calc_rsi(
        af: AF,
        base: str,
        period: int
) -> float:
    l = len(af.bar_data)
    if l < period:
        return 0
    return ta.RSI(af.bar_data[base], period).iloc[-1]


@T.cache(
    param_name='emas',
    param={
        '1': [1],
        '2': [1]
    }
)
def calc_dif(
        price: float,
        period_s: int,
        period_l: int,
        emas: Optional[dict[str, list]] = None
) -> float:
    """
    DIF
    the price of short period ema - the price of long period ema

    Args:
        price:
        period_s:
        period_l:
        emas:

    Returns:
        float: dif value

    """
    ema1_lst = emas['1']
    ema2_lst = emas['2']
    ma1 = ema(price, period_s, ema1_lst[-1])
    ma2 = ema(price, period_l, ema2_lst[-1])
    ema1_lst.append(ma1)
    ema2_lst.append(ma2)

    dif = ma1 - ma2
    return dif


def calc_dea(
        dif: float,
        period: int,
        last_dea: float
) -> float:
    """
    DEA

    Args:
        dif:
        period: period
        last_dea:

    Returns:
        float: dea value

    """
    dif_ema = ema(dif, period, last_dea)
    return dif_ema


@T.cache(
    param_name='last_dea',
    param=[0]
)
def calc_macd(
        price: float,
        period_s: int,
        period_l: int,
        period_m: int,
        last_dea: list[float]
) -> tuple[float, float, float]:
    """MACD indicator

    有些小问题

    Args:
        price:
        period_s: the period of DIFF short
        period_l: the period of DIFF long
        period_m: the period of DEA
        last_dea:

    Returns:
        tuple[float, float, float]: macd, dif, dea

    """
    dif = calc_dif(price, period_s, period_l)
    dea = calc_dea(dif, period_m, last_dea[0])
    macd = 2 * (dif - dea)
    last_dea[0] = dea
    return macd, dif, dea


def calc_sar(
        af: AF,
        last_sar: float,
        bull: bool,
        wtf_high_price: float = 0,
        wtf_low_price: float = 0,
        af_init: Optional[float] = 0.02,
        base_af: Optional[float] = 0.02,
        max_af: Optional[float] = 0.2
) -> tuple[float, float, float, float, float]:
    """
    SAR indicator

    Args:
        af:
        last_sar: 历史 SAR
        bull: 历史 bull
        wtf_high_price: some high price?
        wtf_low_price: some low price?
        af_init: 历史 AF
        base_af: 基础值 AF
        max_af: 最大 AF

    Returns:
        tuple[float, float, float, float, float]: sar, af, bull, wtf_high_price, wtf_low_price

    """
    if len(af.bar_data) == 0:
        return 0, af_init, bull, wtf_high_price, wtf_low_price
    elif len(af.bar_data) < 3:
        return af.bar_data.iloc[-1].close, af_init, bull, wtf_high_price, wtf_low_price

    bar = af.bar_data.iloc[-1]
    last_bar = af.bar_data.iloc[-2]
    high_price = bar.high
    low_price = bar.low
    last_high_price = last_bar.high
    last_low_price = last_bar.low

    reverse = False
    if bull:
        sar = last_sar + af_init * (wtf_high_price - last_sar)
    else:
        sar = last_sar + af_init * (wtf_low_price - last_sar)
    if bull:
        if low_price < sar:
            bull = False
            reverse = True
            sar = wtf_high_price
            wtf_low_price = low_price
            af_init = base_af
    else:
        if high_price > sar:
            bull = True
            reverse = True
            sar = wtf_low_price
            wtf_high_price = high_price
            af_init = base_af

    if not reverse:
        if bull:
            if high_price > wtf_high_price:
                wtf_high_price = high_price
                af_init = min(af_init + base_af, max_af)
            if last_low_price < sar:
                sar = last_low_price
            if last_bar.low < sar:
                sar = last_bar.low
        else:
            if low_price < wtf_low_price:
                wtf_low_price = low_price
                af_init = min(af_init + base_af, max_af)
            if last_high_price > sar:
                sar = last_high_price
            if last_bar.high > sar:
                sar = last_bar.high

    return sar, af_init, bull, wtf_high_price, wtf_low_price
