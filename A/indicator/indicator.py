import talib as ta
from A import AF
from .base import *


def rsi(
        af: AF,
        base: str,
        period: int
) -> float:
    l = len(af.bar_data)
    if l < period:
        return 0
    return ta.RSI(af.bar_data[base], period).iloc[-1]


def dif(
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


def macd(
        price: float,
        period_s: int,
        period_l: int,
        period_m: int,
        last_dea: float
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
    dif = dif(price, period_s, period_l)
    dea = dea(dif, period_m, last_dea)
    macd = 2 * (dif - dea)
    self.dif_list.append(dif)
    return macd, dif, dea
