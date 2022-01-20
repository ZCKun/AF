import talib as ta
import functools

from A import AF
from .base import ema
from typing import Optional, Any


class T:
    @staticmethod
    def cache(
            param_name: Optional[str] = None,
            param: Optional[Any] = None
    ):
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


@T.cache(param_name='last_dea', param=[0])
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
