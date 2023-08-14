from enum import Enum, IntEnum

import pytest

from adaptix import dumper, enum_by_value, loader
from adaptix._internal.provider.enum_provider import EnumExactValueProvider, EnumNameProvider
from adaptix.load_error import BadVariantError, MsgError
from tests_helpers import TestRetort, parametrize_bool, raises_path


class MyEnum(Enum):
    V1 = "1"


class MyIntEnum(IntEnum):
    V1 = 1


class MyEnumWithMissingHook(Enum):
    V1 = '1'

    @classmethod
    def _missing_(cls, value: object) -> 'MyEnumWithMissingHook':
        raise ValueError


@parametrize_bool('strict_coercion', 'debug_path')
def test_name_provider(strict_coercion, debug_path):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
        recipe=[
            EnumNameProvider(),
        ],
    )

    loader = retort.get_loader(MyEnum)

    assert loader("V1") == MyEnum.V1

    raises_path(
        BadVariantError(['V1']),
        lambda: loader("1")
    )

    raises_path(
        BadVariantError(['V1']),
        lambda: loader(1)
    )

    raises_path(
        BadVariantError(['V1']),
        lambda: loader(MyEnum.V1)
    )

    dumper = retort.get_dumper(MyEnum)

    assert dumper(MyEnum.V1) == "V1"


@parametrize_bool('strict_coercion', 'debug_path')
@pytest.mark.parametrize('enum_cls', [MyEnum, MyEnumWithMissingHook])
def test_exact_value_provider(strict_coercion, debug_path, enum_cls):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
        recipe=[
            EnumExactValueProvider(),
        ],
    )

    loader = retort.get_loader(enum_cls)

    assert loader("1") == enum_cls.V1

    raises_path(
        BadVariantError(['1']),
        lambda: loader("V1")
    )

    raises_path(
        BadVariantError(['1']),
        lambda: loader(1)
    )

    raises_path(
        BadVariantError(['1']),
        lambda: loader(enum_cls.V1)
    )

    dumper = retort.get_dumper(enum_cls)

    assert dumper(enum_cls.V1) == "1"


@parametrize_bool('strict_coercion', 'debug_path')
def test_exact_value_provider_int_enum(strict_coercion, debug_path):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
        recipe=[
            EnumExactValueProvider(),
        ],
    )
    int_enum_loader = retort.get_loader(MyIntEnum)

    assert int_enum_loader(1) == MyIntEnum.V1

    raises_path(
        BadVariantError([1]),
        lambda: int_enum_loader(MyEnum.V1),
    )

    raises_path(
        BadVariantError([1]),
        lambda: int_enum_loader("V1")
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_exact_value_optimization(strict_coercion, debug_path):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
        recipe=[
            EnumExactValueProvider(),
        ],
    )
    assert retort.get_loader(MyEnum).__name__ == 'enum_exact_loader_v2m'
    assert retort.get_loader(MyEnumWithMissingHook).__name__ == 'enum_exact_loader'


def custom_string_dumper(value: str):
    return "PREFIX " + value


@parametrize_bool('strict_coercion', 'debug_path')
def test_value_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            enum_by_value(MyEnum, tp=str),
            loader(str, str),
            dumper(str, custom_string_dumper),
        ]
    ).replace(
        strict_coercion=strict_coercion,
        debug_path=debug_path,
    )

    enum_loader = retort.get_loader(MyEnum)

    assert enum_loader("1") == MyEnum.V1
    assert enum_loader(1) == MyEnum.V1

    raises_path(
        MsgError('Bad enum value'),
        lambda: enum_loader("V1")
    )

    raises_path(
        MsgError('Bad enum value'),
        lambda: enum_loader(MyEnum.V1)
    )

    enum_dumper = retort.get_dumper(MyEnum)

    assert enum_dumper(MyEnum.V1) == "PREFIX 1"
