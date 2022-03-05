from datetime import datetime

from A.types import BaseEntity
from typing import Optional


class Snapshot(BaseEntity):

    symbol_code: str = ''
    data_time: Optional[datetime] = None
    # the snapshot data received time
    recv_time: int = 0
    exchange_id: int = 0
    # the trading day date
    trading_day: int = 0

    pre_close_price: float = float('nan')
    open_price: float = float('nan')
    high_price: float = float('nan')
    low_price: float = float('nan')
    last_price: float = float('nan')
    # current trade volume
    trade_volume: int = 0
    # current trade turnover
    trade_turnover: float = float('nan')
    # total trade volume on day
    total_trade_volume: int = 0
    # total trade turnover on day
    total_trade_turnover: int = 0
    upper_limit_price: float = float('nan')
    lower_limit_price: float = float('nan')

    bid: Optional[list[float]] = None
    ask: Optional[list[float]] = None
    ask_qty: Optional[list[int]] = None
    bid_qty: Optional[list[int]] = None

    bid1_qty: Optional[list[int]] = None
    bid1_count: int = 0
    max_bid1_count: int = 0

    ask1_qty: Optional[list[int]] = None
    ask1_count: int = 0
    max_ask1_count: int = 0
