from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, IntEnum
from functools import total_ordering
from typing import List, Literal, Optional, Union

import phonenumbers
from phonenumbers import PhoneNumber

from dataclass_factory_30.facade import Factory, parser, serializer
from dataclass_factory_30.facade.provider import enum_by_name
from dataclass_factory_30.provider import NameMapper, ValueParseError
from dataclass_factory_30.provider.model import ExtraSkip

# Module describing Money class


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


def rubles(value: Union[int, str, Decimal]):
    if isinstance(value, int):
        return Money(value)
    return Money.from_decimal_rubles(Decimal(value))


# Module only storing models

class ReceiptType(Enum):
    INCOME = 1
    INCOME_REFUND = 2


class Taxation(IntEnum):
    ORN = 1
    USN = 2
    USN_MINUS = 4
    ESN = 16
    PSN = 32


@dataclass
class NotifyEmail:
    value: str
    type: Literal["email"] = "email"


@dataclass
class NotifyPhone:
    value: PhoneNumber
    type: Literal["phone"] = "phone"


NotifyTarget = Union[NotifyEmail, NotifyPhone]


@dataclass(frozen=True)
class RecItem:
    name: str
    price: Money
    quantity: Decimal


@dataclass(frozen=True)
class Receipt:
    type: ReceiptType
    items: List[RecItem]
    taxation: Taxation
    notify: Optional[List[NotifyTarget]]
    version: Literal[1] = 1


# Module describing how create model from raw input data


def serialize_phone_number(num_obj: PhoneNumber):
    return phonenumbers.format_number(num_obj, phonenumbers.PhoneNumberFormat.E164)


def money_parser(data):
    try:
        return Money.from_decimal_rubles(data)
    except TooPreciseAmount:
        raise ValueParseError("Rubles cannot have more than 2 decimal places")


class BaseFactory(Factory):
    recipe = [
        parser(Money, money_parser),
        serializer(Money, Money.rubles),

        parser(PhoneNumber, phonenumbers.parse),
        serializer(PhoneNumber, serialize_phone_number),

        serializer(Decimal, lambda x: x),
        enum_by_name(ReceiptType),
    ]


# Outer factories use only to create Receipt from api users and have additional validations and conversions,
# inner factories can parse and serialize validated Receipt object, so it uses only at internal messaging

INNER_RECEIPT_FACTORY = BaseFactory(
    recipe=[
        NameMapper(omit_default=False),
    ],
    extra_policy=ExtraSkip(),
)


receipt_parser = INNER_RECEIPT_FACTORY.parser(Receipt)
receipt_serializer = INNER_RECEIPT_FACTORY.serializer(Receipt)

data = {
        "type": "INCOME",
        "items": [
            {
                "name": "Matchbox",
                "price": Decimal("10.0"),
                "quantity": Decimal("3.0"),
            }
        ],
        "taxation": 4,
        "notify": [
            {"type": "email", "value": "mail@example.com"}
        ],
        "version": 1,
    }

parsed_data = receipt_parser(data)
print(parsed_data)
serialized_data = receipt_serializer(parsed_data)
print(serialized_data)
