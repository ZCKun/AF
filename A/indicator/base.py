import numpy as np


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
