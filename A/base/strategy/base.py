from abc import ABC
from typing import Optional

import A


class Strategy(ABC):

    def __init__(self):
        self._type = ...
        self._sub_codes: list[str] = list()
        self.af: Optional[A.AF] = None

    def type(self):
        return self._type

    @property
    def sub_symbol_code(self) -> list[str]:
        return self._sub_codes

    @sub_symbol_code.setter
    def sub_symbol_code(self, symbol_code: list[str]):
        self._sub_codes += symbol_code

    def on_bar(self, bar):
        raise NotImplementedError

    def on_snapshot(self, tick):
        raise NotImplementedError
