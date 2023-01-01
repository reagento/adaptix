from enum import Enum, IntEnum

from dataclass_factory_30.facade import dumper, enum_by_value, loader
from dataclass_factory_30.provider import (
    DumperRequest,
    EnumExactValueProvider,
    EnumNameProvider,
    LoaderRequest,
    TypeHintLocation,
)
from dataclass_factory_30.provider.exceptions import BadVariantError, MsgError
from tests_helpers import TestRetort, parametrize_bool, raises_path


class MyEnum(Enum):
    V1 = "1"


class MyIntEnum(IntEnum):
    V1 = 1


@parametrize_bool('strict_coercion', 'debug_path')
def test_name_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            EnumNameProvider(),
        ]
    )

    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=MyEnum),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

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

    dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=MyEnum),
            debug_path=debug_path,
        )
    )

    assert dumper(MyEnum.V1) == "V1"


@parametrize_bool('strict_coercion', 'debug_path')
def test_exact_value_provider(strict_coercion, debug_path):
    retort = TestRetort(
        recipe=[
            EnumExactValueProvider(),
        ]
    )

    loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=MyEnum),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert loader("1") == MyEnum.V1

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
        lambda: loader(MyEnum.V1)
    )

    dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=MyEnum),
            debug_path=debug_path,
        )
    )

    assert dumper(MyEnum.V1) == "1"

    int_enum_loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=MyIntEnum),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert int_enum_loader(1) == MyIntEnum.V1

    raises_path(
        BadVariantError([1]),
        lambda: int_enum_loader(MyEnum.V1),
    )

    raises_path(
        BadVariantError([1]),
        lambda: int_enum_loader("V1")
    )


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
    )

    enum_loader = retort.provide(
        LoaderRequest(
            loc=TypeHintLocation(type=MyEnum),
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

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

    enum_dumper = retort.provide(
        DumperRequest(
            loc=TypeHintLocation(type=MyEnum),
            debug_path=debug_path,
        )
    )

    assert enum_dumper(MyEnum.V1) == "PREFIX 1"
