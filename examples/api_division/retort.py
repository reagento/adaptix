from decimal import Decimal
from typing import List

import phonenumbers
from phonenumbers import PhoneNumber

from dataclass_factory import Retort, bound, dumper, enum_by_name, loader, name_mapping, validator
from dataclass_factory.load_error import ExtraFieldsError, ValueLoadError
from dataclass_factory.provider import Chain, ExtraForbid, ExtraSkip

from .models import Receipt, ReceiptType, RecItem
from .money import Money, TooPreciseAmount


def load_phone_number(num_obj: PhoneNumber):
    return phonenumbers.format_number(num_obj, phonenumbers.PhoneNumberFormat.E164)


CP866_CHAR_REPLACES = str.maketrans({"«": '"', "»": '"'})


def string_cp866_mutator(data: str):
    t_data = data.translate(CP866_CHAR_REPLACES)
    try:
        t_data.encode("cp866", "strict")
    except UnicodeEncodeError as e:
        bad_char = e.object[e.start: e.end]  # pylint: disable=unsubscriptable-object
        raise ValueLoadError(f'Char {bad_char!r} can not be represented at CP866')
    return t_data


def outer_phonenumber_loader(data: str):
    try:
        phone_number = phonenumbers.parse(data)
    except phonenumbers.NumberParseException:
        raise ValueLoadError('Bad phone number')

    expected = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

    if data != expected:
        raise ValueLoadError('Bad phone number')

    return phone_number


def money_loader(data):
    try:
        return Money.from_decimal_rubles(data)
    except TooPreciseAmount:
        raise ValueLoadError("Rubles cannot have more than 2 decimal places")


def forbid_version_key(data):
    if isinstance(data, dict) and 'version' in data:
        raise ExtraFieldsError(['version'])
    return data


class ParentRetort(Retort):
    recipe = [
        loader(Money, money_loader),
        dumper(Money, Money.rubles),

        loader(PhoneNumber, phonenumbers.parse),
        dumper(PhoneNumber, load_phone_number),

        dumper(Decimal, lambda x: x),
        enum_by_name(ReceiptType),
    ]


INNER_RECEIPT_RETORT = ParentRetort(
    recipe=[
        name_mapping(
            omit_default=False,
            extra_in=ExtraSkip(),
        ),
    ],
)


_OUTER_BASE_RETORT = ParentRetort(
    recipe=[
        loader(PhoneNumber, outer_phonenumber_loader),
        loader(str, string_cp866_mutator, Chain.LAST),
        name_mapping(extra_in=ExtraForbid()),
    ],
)

_OUTER_REC_ITEM_RETORT = _OUTER_BASE_RETORT.extend(
    recipe=[
        validator('quantity', lambda x: x > Decimal(0), 'Value must be > 0'),
        validator('price', lambda x: x >= Money(0), 'Value must be >= 0'),
    ],
)


OUTER_RECEIPT_RETORT = _OUTER_BASE_RETORT.extend(
    recipe=[
        validator(List[RecItem], lambda x: len(x) > 0, 'At least one item must be presented'),
        bound(RecItem, _OUTER_REC_ITEM_RETORT),
        loader(Receipt, forbid_version_key, Chain.FIRST),
    ],
)
