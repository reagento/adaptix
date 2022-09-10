from decimal import Decimal

import phonenumbers
from phonenumbers import PhoneNumber

from dataclass_factory_30.facade import Factory, enum_by_name, parser, serializer
from dataclass_factory_30.provider import ExtraFieldsError, ValueParseError

from models import ReceiptType
from money import Money, TooPreciseAmount


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
