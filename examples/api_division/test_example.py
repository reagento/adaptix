from copy import deepcopy
from decimal import Decimal
from typing import Any, List, Union

import phonenumbers

from dataclass_factory.provider.exceptions import (
    BadVariantError,
    ExtraFieldsError,
    LoadError,
    TypeLoadError,
    UnionLoadError,
    ValidationError,
    ValueLoadError,
)
from tests_helpers import raises_path

from .models import NotifyEmail, NotifyPhone, Receipt, ReceiptType, RecItem, Taxation
from .money import rubles
from .retort import INNER_RECEIPT_RETORT, OUTER_RECEIPT_RETORT


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

outer_receipt_loader = OUTER_RECEIPT_RETORT.get_loader(Receipt)


def test_outer_loading():
    assert outer_receipt_loader(outer_sample_data) == Receipt(
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
        lambda: outer_receipt_loader(no_rec_items_data),
        path=['items'],
    )

    phone_data = change(outer_sample_data, ["notify", 0], {"type": "phone", "value": "+14155552671"})

    assert outer_receipt_loader(phone_data) == Receipt(
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
        UnionLoadError(
            [
                UnionLoadError(
                    [
                        LoadError(),
                        ValueLoadError(msg='Bad phone number')
                    ]
                ),
                TypeLoadError(expected_type=None)
            ]
        ),
        lambda: outer_receipt_loader(bad_phone_data),
        path=['notify'],  # I do not know how to fix that
    )

    bad_receipt_type_data = change(outer_sample_data, ["type"], "BAD_TYPE")

    raises_path(
        BadVariantError(['INCOME', 'INCOME_REFUND']),
        lambda: outer_receipt_loader(bad_receipt_type_data),
        path=['type'],
    )

    with_version_data = change(outer_sample_data, ["version"], 1)

    raises_path(
        ExtraFieldsError(['version']),
        lambda: outer_receipt_loader(with_version_data),
        path=[],
    )


def test_outer_receipt_item_validation():
    bad_quantity_data = change(outer_sample_data, ["items", 0, "quantity"], Decimal(0))

    raises_path(
        ValidationError('Value must be > 0'),
        lambda: outer_receipt_loader(bad_quantity_data),
        path=["items", 0, "quantity"],
    )

    bad_price_data = change(outer_sample_data, ["items", 0, "price"], Decimal(-10))

    raises_path(
        ValidationError('Value must be >= 0'),
        lambda: outer_receipt_loader(bad_price_data),
        path=["items", 0, "price"],
    )

    bad_name_data = change(outer_sample_data, ["items", 0, "name"], 'Matchbox 🔥')

    raises_path(
        ValueLoadError("Char '🔥' can not be represented at CP866"),
        lambda: outer_receipt_loader(bad_name_data),
        path=["items", 0, "name"],
    )

    replace_name_data = change(outer_sample_data, ["items", 0, "name"], 'Matchbox «Dry Fire»')

    assert outer_receipt_loader(replace_name_data) == Receipt(
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
    loaded_data = INNER_RECEIPT_RETORT.load(data, Receipt)
    assert loaded_data == receipt
    dumped_data = INNER_RECEIPT_RETORT.dump(receipt)
    assert dumped_data == data
