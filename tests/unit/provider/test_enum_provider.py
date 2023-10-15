from enum import Enum, IntEnum

import pytest
from tests_helpers import TestRetort, raises_exc

from adaptix import dumper, enum_by_value, loader
from adaptix._internal.provider.enum_provider import EnumExactValueProvider, EnumNameProvider
from adaptix.load_error import BadVariantError, MsgError


class MyEnum(Enum):
    V1 = "1"


class MyIntEnum(IntEnum):
    V1 = 1


class MyEnumWithMissingHook(Enum):
    V1 = '1'

    @classmethod
    def _missing_(cls, value: object) -> 'MyEnumWithMissingHook':
        raise ValueError


def test_name_provider(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            EnumNameProvider(),
        ],
    )

    loader = retort.get_loader(MyEnum)

    assert loader("V1") == MyEnum.V1

    raises_exc(
        BadVariantError(['V1'], '1'),
        lambda: loader("1")
    )

    raises_exc(
        BadVariantError(['V1'], 1),
        lambda: loader(1)
    )

    raises_exc(
        BadVariantError(['V1'], MyEnum.V1),
        lambda: loader(MyEnum.V1)
    )

    dumper = retort.get_dumper(MyEnum)

    assert dumper(MyEnum.V1) == "V1"


@pytest.mark.parametrize('enum_cls', [MyEnum, MyEnumWithMissingHook])
def test_exact_value_provider(strict_coercion, debug_trail, enum_cls):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            EnumExactValueProvider(),
        ],
    )

    loader = retort.get_loader(enum_cls)

    assert loader("1") == enum_cls.V1

    raises_exc(
        BadVariantError(['1'], 'V1'),
        lambda: loader("V1")
    )

    raises_exc(
        BadVariantError(['1'], 1),
        lambda: loader(1)
    )

    raises_exc(
        BadVariantError(['1'], enum_cls.V1),
        lambda: loader(enum_cls.V1)
    )

    dumper = retort.get_dumper(enum_cls)

    assert dumper(enum_cls.V1) == "1"


def test_exact_value_provider_int_enum(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            EnumExactValueProvider(),
        ],
    )
    int_enum_loader = retort.get_loader(MyIntEnum)

    assert int_enum_loader(1) == MyIntEnum.V1

    raises_exc(
        BadVariantError([1], MyEnum.V1),
        lambda: int_enum_loader(MyEnum.V1),
    )

    raises_exc(
        BadVariantError([1], 'V1'),
        lambda: int_enum_loader("V1")
    )


def test_exact_value_optimization(strict_coercion, debug_trail):
    assert EnumExactValueProvider()._make_loader(MyEnum).__name__ == 'enum_exact_loader_v2m'
    assert EnumExactValueProvider()._make_loader(MyEnumWithMissingHook).__name__ == 'enum_exact_loader'


def custom_string_dumper(value: str):
    return "PREFIX " + value


def test_value_provider(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            enum_by_value(MyEnum, tp=str),
            loader(str, str),
            dumper(str, custom_string_dumper),
        ],
    )

    enum_loader = retort.get_loader(MyEnum)

    assert enum_loader("1") == MyEnum.V1
    assert enum_loader(1) == MyEnum.V1

    raises_exc(
        MsgError('Bad enum value', "V1"),
        lambda: enum_loader("V1")
    )

    raises_exc(
        MsgError('Bad enum value', MyEnum.V1),
        lambda: enum_loader(MyEnum.V1)
    )

    enum_dumper = retort.get_dumper(MyEnum)

    assert enum_dumper(MyEnum.V1) == "PREFIX 1"
