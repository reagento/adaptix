from enum import Enum, IntEnum

from dataclass_factory_30.facade import enum_by_value, parser, serializer
from dataclass_factory_30.provider import (
    EnumExactValueProvider,
    EnumNameProvider,
    ParseError,
    ParserRequest,
    SerializerRequest,
)
from dataclass_factory_30.provider.definitions import BadVariantError, MsgError
from tests_helpers import TestFactory, parametrize_bool, raises_path


class MyEnum(Enum):
    V1 = "1"


class MyIntEnum(IntEnum):
    V1 = 1


@parametrize_bool('strict_coercion', 'debug_path')
def test_name_provider(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[
            EnumNameProvider(),
        ]
    )

    parser = factory.provide(
        ParserRequest(
            type=MyEnum,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser("V1") == MyEnum.V1

    raises_path(
        BadVariantError(['V1']),
        lambda: parser("1")
    )

    raises_path(
        BadVariantError(['V1']),
        lambda: parser(1)
    )

    raises_path(
        BadVariantError(['V1']),
        lambda: parser(MyEnum.V1)
    )

    serializer = factory.provide(
        SerializerRequest(
            type=MyEnum,
            debug_path=debug_path,
        )
    )

    assert serializer(MyEnum.V1) == "V1"


@parametrize_bool('strict_coercion', 'debug_path')
def test_exact_value_provider(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[
            EnumExactValueProvider(),
        ]
    )

    parser = factory.provide(
        ParserRequest(
            type=MyEnum,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert parser("1") == MyEnum.V1

    raises_path(
        BadVariantError(['1']),
        lambda: parser("V1")
    )

    raises_path(
        BadVariantError(['1']),
        lambda: parser(1)
    )

    raises_path(
        BadVariantError(['1']),
        lambda: parser(MyEnum.V1)
    )

    serializer = factory.provide(
        SerializerRequest(
            type=MyEnum,
            debug_path=debug_path,
        )
    )

    assert serializer(MyEnum.V1) == "1"

    int_enum_parser = factory.provide(
        ParserRequest(
            type=MyIntEnum,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert int_enum_parser(1) == MyIntEnum.V1

    raises_path(
        BadVariantError([1]),
        lambda: int_enum_parser(MyEnum.V1),
    )

    raises_path(
        BadVariantError([1]),
        lambda: int_enum_parser("V1")
    )


def custom_string_serializer(value: str):
    return "PREFIX " + value


@parametrize_bool('strict_coercion', 'debug_path')
def test_value_provider(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[
            enum_by_value(MyEnum, tp=str),
            parser(str),
            serializer(str, custom_string_serializer),
        ]
    )

    enum_parser = factory.provide(
        ParserRequest(
            type=MyEnum,
            strict_coercion=strict_coercion,
            debug_path=debug_path,
        )
    )

    assert enum_parser("1") == MyEnum.V1
    assert enum_parser(1) == MyEnum.V1

    raises_path(
        MsgError('Bad enum value'),
        lambda: enum_parser("V1")
    )

    raises_path(
        MsgError('Bad enum value'),
        lambda: enum_parser(MyEnum.V1)
    )

    enum_serializer = factory.provide(
        SerializerRequest(
            type=MyEnum,
            debug_path=debug_path,
        )
    )

    assert enum_serializer(MyEnum.V1) == "PREFIX 1"
