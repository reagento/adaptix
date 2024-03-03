from decimal import Decimal
from typing import List

import phonenumbers
from phonenumbers import PhoneNumber

from adaptix import Chain, ExtraForbid, ExtraSkip, P, Retort, dumper, enum_by_name, loader, name_mapping, validator
from adaptix.load_error import ExtraFieldsLoadError, ValueLoadError

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
        raise ValueLoadError(f"Char {bad_char!r} can not be represented at CP866", data)
    return t_data


def outer_phonenumber_loader(data: str):
    try:
        phone_number = phonenumbers.parse(data)
    except phonenumbers.NumberParseException:
        raise ValueLoadError("Bad phone number", data)

    expected = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

    if data != expected:
        raise ValueLoadError("Bad phone number", data)

    return phone_number


def money_loader(data):
    try:
        return Money.from_decimal_rubles(data)
    except TooPreciseAmount:
        raise ValueLoadError("Rubles cannot have more than 2 decimal places", data)


def forbid_version_key(data):
    if isinstance(data, dict) and "version" in data:
        raise ExtraFieldsLoadError(["version"], data)
    return data


_base_retort = Retort(
    recipe=[
        loader(Money, money_loader),
        dumper(Money, Money.rubles),

        loader(PhoneNumber, phonenumbers.parse),
        dumper(PhoneNumber, load_phone_number),

        # We need to represent Decimal as JSON float instead of string.
        # JSON serializer library will take pure Decimal and produce JSON float,
        # without intermediate casting to float (standard json package can do this)
        dumper(Decimal, lambda x: x),

        enum_by_name(ReceiptType),
    ],
)


inner_receipt_retort = _base_retort.extend(
    recipe=[
        name_mapping(extra_in=ExtraSkip()),
    ],
)

outer_receipt_retort = _base_retort.extend(
    recipe=[
        validator(List[RecItem], lambda x: len(x) > 0, "At least one item must be presented"),
        validator(P[RecItem].quantity, lambda x: x > Decimal(0), "Value must be > 0"),
        validator(P[RecItem].price, lambda x: x >= Money(0), "Value must be >= 0"),

        loader(Receipt, forbid_version_key, Chain.FIRST),  # function will be applied BEFORE builtin loader
        loader(PhoneNumber, outer_phonenumber_loader),  # function will be applied INSTEAD OF builtin loader
        loader(str, string_cp866_mutator, Chain.LAST),  # function will be applied AFTER builtin loader

        name_mapping(extra_in=ExtraForbid()),
    ],
)
