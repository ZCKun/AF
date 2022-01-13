from enum import IntEnum


class Color(IntEnum):
    pass


class Light(Color):
    WHITE = 1
    RED = 91
    GREEN = 92
    YELLOW = 93
    BLUE = 94
    PURPLE = 95
    CYAN_BLUE = 96


class Deep(Color):
    WHITE = 0
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    PURPLE = 35
    CYAN_BLUE = 36


def make_color_func(color: str) -> str:
    pass
