from decimal import Decimal
from functools import total_ordering
from typing import Union


class TooPreciseAmount(Exception):
    pass


@total_ordering
class Money:
    __slots__ = ("kopek",)

    def __init__(self, kopek: int):
        self.kopek = kopek

    def __eq__(self, other):
        if isinstance(other, Money):
            return self.kopek == other.kopek
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Money):
            return self.kopek > other.kopek
        return NotImplemented

    def __repr__(self):
        return f"{self.rubles():.2f}₽"

    def rubles(self) -> Decimal:
        return Decimal(self.kopek) / 100

    @classmethod
    def from_decimal_rubles(cls, rubles_: Decimal):
        kopek = rubles_ * 100
        if kopek % 1 != 0:
            raise TooPreciseAmount
        return cls(int(kopek))


def rubles(value: Union[int, str, Decimal]) -> Money:
    return Money.from_decimal_rubles(Decimal(value))
