from datetime import datetime

from A.types import BaseEntity
from typing import Optional


class OrderBook(BaseEntity):

    symbol_code: str = ''
    data_time: Optional[datetime] = None
    # the snapshot data received time
    recv_time: int = 0
    exchange_id: int = 0

    last_price: float = float('nan')
    qty: int = 0
    turnover: float = float('nan')
    trades_count: int = 0

    bids: Optional[list[tuple]] = None
    asks: Optional[list[tuple]] = None

