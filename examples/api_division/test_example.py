from copy import deepcopy
from decimal import Decimal
from typing import Any, List, Union

import phonenumbers

from dataclass_factory_30.facade.provider import ValidationError
from dataclass_factory_30.provider import ExtraFieldsError, ParseError, TypeParseError, UnionParseError, ValueParseError
from dataclass_factory_30.provider.errors import BadVariantError
from tests_helpers import raises_path

from .factory import INNER_RECEIPT_FACTORY, OUTER_RECEIPT_FACTORY
from .models import NotifyEmail, NotifyPhone, Receipt, ReceiptType, RecItem, Taxation
from .money import rubles


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
        BadVariantError(['INCOME', 'INCOME_REFUND']),
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
        ValueParseError("Char '🔥' can not be represented at CP866"),
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
