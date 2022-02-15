from datetime import datetime

from A.types import BaseEntity, Price


class Snapshot(BaseEntity):

    symbol_code: str
    data_time: datetime
    # the snapshot data received time
    recv_time: int
    exchange_id: int
    # the trading day date
    trading_day: int

    pre_close_price: Price
    open_price: Price
    high_price: Price
    low_price: Price
    last_price: Price
    # current trade volume
    trade_volume: int
    # current trade turnover
    trade_turnover: Price
    # total trade volume on day
    total_trade_volume: int
    # total trade turnover on day
    total_trade_turnover: int
    upper_limit_price: Price
    lower_limit_price: Price

    bid: list[Price]
    ask: list[Price]
    ask_qty: list[int]
    bid_qty: list[int]

    bid1_qty: list[int]
    bid1_count: int
    max_bid1_count: int

    ask1_qty: list[int]
    ask1_count: int
    max_ask1_count: int

    def __init__(self, **data):
        self.__dict__.update(data)
