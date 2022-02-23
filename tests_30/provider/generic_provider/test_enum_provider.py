from enum import Enum, IntEnum

import pytest

from dataclass_factory_30.common import Serializer, Parser
from dataclass_factory_30.provider import (
    EnumNameProvider,
    EnumExactValueProvider,
    EnumValueProvider,
    ParserRequest,
    SerializerRequest,
    ParseError,
    as_serializer,
    as_parser,
    CannotProvide,
    Mediator
)
from dataclass_factory_30.provider.generic_provider import BaseEnumProvider
from tests_30.provider.conftest import TestFactory, parametrize_bool, raises_instance


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

    raises_instance(
        ParseError(),
        lambda: parser("1")
    )

    raises_instance(
        ParseError(),
        lambda: parser(1)
    )

    raises_instance(
        ParseError(),
        lambda: parser(MyEnum.V1)
    )

    serializer = factory.provide(
        SerializerRequest(
            type=MyEnum,
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

    raises_instance(
        ParseError(),
        lambda: parser("V1")
    )

    raises_instance(
        ParseError(),
        lambda: parser(1)
    )

    raises_instance(
        ParseError(),
        lambda: parser(MyEnum.V1)
    )

    serializer = factory.provide(
        SerializerRequest(
            type=MyEnum,
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

    raises_instance(
        ParseError(),
        lambda: int_enum_parser(MyEnum.V1)
    )

    raises_instance(
        ParseError(),
        lambda: int_enum_parser("V1")
    )


def custom_string_serializer(value: str):
    return "PREFIX " + value


@parametrize_bool('strict_coercion', 'debug_path')
def test_value_provider(strict_coercion, debug_path):
    factory = TestFactory(
        recipe=[
            EnumValueProvider([MyEnum], value_type=str),
            as_parser(str),
            as_serializer(str, custom_string_serializer),
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
    assert parser(1) == MyEnum.V1

    raises_instance(
        ParseError(),
        lambda: parser("V1")
    )

    raises_instance(
        ParseError(),
        lambda: parser(MyEnum.V1)
    )

    serializer = factory.provide(
        SerializerRequest(
            type=MyEnum,
        )
    )

    assert serializer(MyEnum.V1) == "PREFIX 1"


class TestEnumProvider(BaseEnumProvider):
    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        pass

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        pass


@parametrize_bool('strict_coercion', 'debug_path')
def test_provider_selecting_any(strict_coercion, debug_path):
    all_enums = TestEnumProvider(bounds=None)

    for tp in [MyEnum, MyIntEnum]:
        all_enums._check_request(
            ParserRequest(
                type=tp,
                strict_coercion=strict_coercion,
                debug_path=debug_path
            )
        )

        all_enums._check_request(
            SerializerRequest(
                type=tp,
            )
        )


@parametrize_bool('strict_coercion', 'debug_path')
def test_provider_selecting_iter(strict_coercion, debug_path):
    my_enum = TestEnumProvider(bounds=[MyEnum])

    my_enum._check_request(
        ParserRequest(
            type=MyEnum,
            strict_coercion=strict_coercion,
            debug_path=debug_path
        )
    )

    my_enum._check_request(
        SerializerRequest(
            type=MyEnum,
        )
    )

    raises_instance(
        CannotProvide(),
        lambda: my_enum._check_request(
            ParserRequest(
                type=MyIntEnum,
                strict_coercion=strict_coercion,
                debug_path=debug_path
            )
        )
    )

    raises_instance(
        CannotProvide(),
        lambda: my_enum._check_request(
            SerializerRequest(
                type=MyIntEnum,
            )
        )
    )


@parametrize_bool('strict_coercion', 'debug_path')
def test_provider_selecting_int_enum(strict_coercion, debug_path):
    my_int_enum = TestEnumProvider(bounds=[MyIntEnum])

    raises_instance(
        CannotProvide(),
        lambda: my_int_enum._check_request(
            ParserRequest(
                type=int,
                strict_coercion=strict_coercion,
                debug_path=debug_path
            )
        )
    )

    raises_instance(
        CannotProvide(),
        lambda: my_int_enum._check_request(
            SerializerRequest(
                type=int,
            )
        )
    )


def test_constructor_exception_raising():
    with pytest.raises(ValueError):
        TestEnumProvider(bounds=[Enum])
