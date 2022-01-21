import copy
import weakref

from enum import Enum
from collections.abc import MutableMapping


class BuySell(Enum):
    Buy = 1
    Sell = 2


class Price:

    def __init__(self, value=0):
        try:
            self._price = int(value * 1000)
        except OverflowError as e:
            self._price = 0

    def __lt__(self, other):
        if isinstance(other, float):
            other = int(other * 1000)
        elif isinstance(other, Price):
            other = other._price

        return self._price < other

    def __gt__(self, other):
        if isinstance(other, float):
            other = int(other * 1000)
        elif isinstance(other, Price):
            other = other._price

        return self._price > other

    def __le__(self, other):
        if isinstance(other, float):
            other = int(other * 1000)
        elif isinstance(other, Price):
            other = other._price

        return self._price <= other

    def __ne__(self, other):
        if isinstance(other, float):
            other = int(other * 1000)
        elif isinstance(other, Price):
            other = other._price

        return self._price != other

    def __ge__(self, other):
        if isinstance(other, float):
            other = int(other * 1000)
        elif isinstance(other, Price):
            other = other._price

        return self._price >= other

    def __add__(self, other):
        if isinstance(other, Price):
            other = other._price
        elif isinstance(other, float):
            other = int(other * 1000)

        self._price += other
        return self

    def __repr__(self):
        return str(self._price / 1000)


class BaseEntity(MutableMapping):

    def _instance_entity(self, path):
        self._path = path
        self._listener = weakref.WeakSet()

    def __setitem__(self, key, value):
        return self.__dict__.__setitem__(key, value)

    def __delitem__(self, key):
        return self.__dict__.__delitem__(key)

    def __getitem__(self, key):
        return self.__dict__.__getitem__(key)

    def __iter__(self):
        return iter({k: v for k, v in self.__dict__.items() if not k.startswith("_")})

    def __len__(self):
        return len({k: v for k, v in self.__dict__.items() if not k.startswith("_")})

    def __str__(self):
        return str({k: v for k, v in self.__dict__.items() if not k.startswith("_")})

    def __repr__(self):
        return '{}, D({})'.format(super(BaseEntity, self).__repr__(),
                                  {k: v for k, v in self.__dict__.items() if not k.startswith("_")})

    def copy(self):
        return copy.copy(self)
