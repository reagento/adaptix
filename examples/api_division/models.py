from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, IntEnum
from typing import List, Literal, Optional, Union

from phonenumbers import PhoneNumber

from .money import Money


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
    version: Literal['1'] = '1'
