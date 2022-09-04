from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, IntEnum
from functools import total_ordering
from typing import Any, List, Literal, Optional, Union

import phonenumbers
from phonenumbers import PhoneNumber

from dataclass_factory_30.facade import Factory, parser, serializer
from dataclass_factory_30.facade.provider import bound, enum_by_name, validator
from dataclass_factory_30.provider import (
    Chain,
    ExtraFieldsError,
    NameMapper,
    ParseError,
    TypeParseError,
    UnionParseError,
    ValidationError,
    ValueParseError,
)
from dataclass_factory_30.provider.model import ExtraForbid, ExtraSkip
from tests_helpers import raises_path

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


CP866_CHAR_REPLACES = str.maketrans({"«": '"', "»": '"'})


def string_cp866_mutator(data: str):
    t_data = data.translate(CP866_CHAR_REPLACES)
    try:
        t_data.encode("cp866", "strict")
    except UnicodeEncodeError as e:
        bad_char = e.object[e.start: e.end]
        raise ValueParseError(f'Char {bad_char!r} can not be represented at CP866')
    return t_data


def outer_phonenumber_parser(data: str):
    try:
        phone_number = phonenumbers.parse(data)
    except phonenumbers.NumberParseException:
        raise ValueParseError('Bad phone number')

    expected = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

    if data != expected:
        raise ValueParseError('Bad phone number')

    return phone_number


def money_parser(data):
    try:
        return Money.from_decimal_rubles(data)
    except TooPreciseAmount:
        raise ValueParseError("Rubles cannot have more than 2 decimal places")


def forbid_version_key(data):
    if isinstance(data, dict) and 'version' in data:
        raise ExtraFieldsError(['version'])
    return data


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


class BaseOuterFactory(BaseFactory):
    recipe = [
        parser(PhoneNumber, outer_phonenumber_parser),
        parser(str, string_cp866_mutator, Chain.LAST),
    ]


OUTER_REC_ITEM_FACTORY = BaseOuterFactory(
    recipe=[
        validator('quantity', lambda x: x > Decimal(0), 'Value must be > 0'),
        validator('price', lambda x: x >= Money(0), 'Value must be >= 0'),
    ],
    extra_policy=ExtraForbid(),
)
OUTER_RECEIPT_FACTORY = BaseOuterFactory(
    recipe=[
        validator(List[RecItem], lambda x: len(x) > 0, 'At least one item must be presented'),
        bound(RecItem, OUTER_REC_ITEM_FACTORY),
        parser(Receipt, forbid_version_key, Chain.FIRST),
    ],
    extra_policy=ExtraForbid(),
)


def change(data, path: List[Union[str, int]], new_value: Any):
    new_data = deepcopy(data)

    target = new_data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = new_value

    return new_data


outer_sample_data = {
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
}

outer_receipt_parser = OUTER_RECEIPT_FACTORY.parser(Receipt)


def test_outer_parsing():
    assert outer_receipt_parser(outer_sample_data) == Receipt(
        type=ReceiptType.INCOME,
        items=[
            RecItem(
                name="Matchbox",
                price=rubles("10"),
                quantity=Decimal(3),
            )
        ],
        taxation=Taxation.USN_MINUS,
        notify=[NotifyEmail("mail@example.com")],
    )

    no_rec_items_data = change(outer_sample_data, ["items"], [])

    raises_path(
        ValidationError('At least one item must be presented'),
        lambda: outer_receipt_parser(no_rec_items_data),
        path=['items'],
    )

    phone_data = change(outer_sample_data, ["notify", 0], {"type": "phone", "value": "+14155552671"})

    assert outer_receipt_parser(phone_data) == Receipt(
        type=ReceiptType.INCOME,
        items=[
            RecItem(
                name="Matchbox",
                price=rubles("10"),
                quantity=Decimal(3),
            )
        ],
        taxation=Taxation.USN_MINUS,
        notify=[NotifyPhone(phonenumbers.parse("+14155552671"))],
    )

    bad_phone_data = change(outer_sample_data, ["notify", 0], {"type": "phone", "value": "+1-541-754-3010"})

    raises_path(
        UnionParseError(
            [
                UnionParseError(
                    [
                        ParseError(),
                        ValueParseError(msg='Bad phone number')
                    ]
                ),
                TypeParseError(expected_type=None)
            ]
        ),
        lambda: outer_receipt_parser(bad_phone_data),
        path=['notify'],  # I do not know how to fix that
    )

    bad_receipt_type_data = change(outer_sample_data, ["type"], "BAD_TYPE")

    raises_path(
        ParseError(),
        lambda: outer_receipt_parser(bad_receipt_type_data),
        path=['type'],
    )

    with_version_data = change(outer_sample_data, ["version"], 1)

    raises_path(
        ExtraFieldsError(['version']),
        lambda: outer_receipt_parser(with_version_data),
        path=[],
    )


def test_outer_receipt_item_validation():
    bad_quantity_data = change(outer_sample_data, ["items", 0, "quantity"], Decimal(0))

    raises_path(
        ValidationError('Value must be > 0'),
        lambda: outer_receipt_parser(bad_quantity_data),
        path=["items", 0, "quantity"],
    )

    bad_price_data = change(outer_sample_data, ["items", 0, "price"], Decimal(-10))

    raises_path(
        ValidationError('Value must be >= 0'),
        lambda: outer_receipt_parser(bad_price_data),
        path=["items", 0, "price"],
    )

    bad_name_data = change(outer_sample_data, ["items", 0, "name"], 'Matchbox 🔥')

    raises_path(
        ValueParseError(f"Char '🔥' can not be represented at CP866"),
        lambda: outer_receipt_parser(bad_name_data),
        path=["items", 0, "name"],
    )

    replace_name_data = change(outer_sample_data, ["items", 0, "name"], 'Matchbox «Dry Fire»')

    assert outer_receipt_parser(replace_name_data) == Receipt(
        type=ReceiptType.INCOME,
        items=[
            RecItem(
                name='Matchbox "Dry Fire"',
                price=rubles("10"),
                quantity=Decimal(3),
            )
        ],
        taxation=Taxation.USN_MINUS,
        notify=[NotifyEmail(value="mail@example.com")],
    )


def test_inner():
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

    receipt = Receipt(
        type=ReceiptType.INCOME,
        items=[
            RecItem(
                name="Matchbox",
                price=rubles("10"),
                quantity=Decimal(3),
            )
        ],
        taxation=Taxation.USN_MINUS,
        notify=[NotifyEmail("mail@example.com")],
    )

    assert receipt_parser(data) == receipt
    serialized_data = receipt_serializer(receipt)
    assert serialized_data == data
