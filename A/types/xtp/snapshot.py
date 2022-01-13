from A.types import BaseEntity


class Snapshot(BaseEntity):

    bid1_qty: list[int]
    bid1_count: int
    max_bid1_count: int

    ask1_qty: list[int]
    ask1_count: int
    max_ask1_count: int

    def __init__(self, **data):
        self.__dict__.update(data)
