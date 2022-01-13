from typing import Any
from enum import Enum
from .strategy import StrategyType


class EventType(Enum):
    SNAPSHOT_DATA: int = 0
    KLINE_DATA: int = 1


class Event:
    data: Any
    event_type: EventType
    ex_type: StrategyType
