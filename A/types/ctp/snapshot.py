from datetime import datetime

from A.types.base import BaseEntity, Price


class Snapshot(BaseEntity):

    trading_day: datetime.date

    # 合约代码
    instrument_id: str
    # 快照时间(处理后)
    time: datetime
    # 快照时间
    update_time: datetime.time
    # 快照时间,毫秒部分
    update_ms: int
    # 最新价
    last_price: Price
    # 开盘价
    open_price: Price
    # 收盘价
    close_price: Price
    # 最高价
    high_price: Price
    # 最低价
    low_price: Price
    # 成交量
    volume: int
    # 成交额
    turnover: Price
    # 未平仓数
    open_interest: int

    # 买5档
    bid1_price: Price
    bid1_volume: int
    bid2_price: Price
    bid2_volume: int
    bid3_price: Price
    bid3_volume: int
    bid4_price: Price
    bid4_volume: int
    bid5_price: Price
    bid5_volume: int

    # 卖5档
    ask1_price: Price
    ask1_volume: int
    ask2_price: Price
    ask2_volume: int
    ask3_price: Price
    ask3_volume: int
    ask4_price: Price
    ask4_volume: int
    ask5_price: Price
    ask5_volume: int

    # 均价
    average_price: Price
    action_day: str
    exchange_id: str
    banding_upper_price: Price
    banding_lower_price: Price

