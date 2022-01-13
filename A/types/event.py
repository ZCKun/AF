from typing import Any


class EventType:
    SNAPSHOT_DATA: int = 0
    KLINE_DATA: int = 1


class Event:
    event_type: EventType
    data: Any
