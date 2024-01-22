from enum import Enum, Flag, IntEnum, auto
from typing import Iterable

import pytest
from tests_helpers import TestRetort, raises_exc

from adaptix import NameStyle, dumper, enum_by_value, loader
from adaptix._internal.morphing.enum_provider import (
    EnumExactValueProvider,
    EnumNameProvider,
    ExactValueEnumMappingGenerator,
    FlagProvider,
    NameEnumMappingGenerator,
)
from adaptix._internal.morphing.load_error import MultipleBadVariant, TypeLoadError, ValueLoadError
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


class FlagEnum(Flag):
    case_one = auto()
    case_two = auto()
    case_three = case_one | case_two
    case_four = auto()
    case_eight = auto()


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


def test_flag_enum_loader(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(NameEnumMappingGenerator()),
        ]
    )

    loader = retort.get_loader(FlagEnum)
    assert loader(["case_one"]) == FlagEnum.case_one
    assert loader(["case_one", "case_two"]) == FlagEnum.case_three
    assert loader(["case_three"]) == FlagEnum.case_three
    assert loader(["case_one", "case_four"]) == FlagEnum.case_one | FlagEnum.case_four
    assert loader(["case_one", "case_one"]) == FlagEnum.case_one

    variants = ["case_one", "case_two", "case_three", "case_four", "case_eight"]
    raises_exc(
        MultipleBadVariant(
            allowed_values=variants,
            input_value=["case_one", "not_existing_case_1", "not_existing_case_2"],
            invalid_values=["not_existing_case_1", "not_existing_case_2"]
        ),
        lambda: loader(["case_one", "not_existing_case_1", "not_existing_case_2"])
    )
    raises_exc(
        TypeLoadError(
            expected_type=Iterable[str],
            input_value="case_one"
        ),
        lambda: loader("case_one")
    )


def test_flag_enum_dumper(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(NameEnumMappingGenerator()),
        ]
    )

    dumper = retort.get_dumper(FlagEnum)
    assert dumper(FlagEnum.case_one) == ["case_one"]
    assert dumper(FlagEnum.case_one | FlagEnum.case_two) == ["case_three"]
    assert dumper(FlagEnum.case_one & FlagEnum.case_two) == []
    assert dumper(FlagEnum.case_two & FlagEnum.case_three) == ["case_two"]
    assert dumper(~FlagEnum.case_two) == ["case_one", "case_four", 'case_eight']


def test_flag_enum_loader_by_exact_value(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(ExactValueEnumMappingGenerator()),
        ]
    )

    loader = retort.get_loader(FlagEnum)
    assert loader([1]) == FlagEnum.case_one
    assert loader([1, 2]) == FlagEnum.case_three
    assert loader([3]) == FlagEnum.case_three
    assert loader([1, 4]) == FlagEnum.case_one | FlagEnum.case_four
    variants = [1, 2, 3, 4, 8]
    raises_exc(
        MultipleBadVariant(
            allowed_values=variants,
            input_value=[1, 2, 5, 6],
            invalid_values=[5, 6]
        ),
        lambda: loader([1, 2, 5, 6])
    )
    raises_exc(
        TypeLoadError(
            expected_type=Iterable[str],
            input_value=1
        ),
        lambda: loader(1)
    )


def test_flag_enum_dumper_by_exact_value(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(ExactValueEnumMappingGenerator()),
        ]
    )

    dumper = retort.get_dumper(FlagEnum)
    assert dumper(FlagEnum.case_one) == [1]
    assert dumper(FlagEnum.case_one | FlagEnum.case_two) == [3]
    assert dumper(FlagEnum.case_one & FlagEnum.case_two) == []
    assert dumper(FlagEnum.case_two & FlagEnum.case_three) == [2]
    assert dumper(~FlagEnum.case_two) == [1, 4, 8]


def test_flag_enum_loader_with_disallowed_compounds(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(NameEnumMappingGenerator(), allow_compound=False),
        ]
    )

    loader = retort.get_loader(FlagEnum)
    assert loader(["case_one"]) == FlagEnum.case_one
    assert loader(["case_one", "case_two"]) == FlagEnum.case_three

    variants = ["case_one", "case_two", "case_four", "case_eight"]
    raises_exc(
        MultipleBadVariant(
            allowed_values=variants,
            input_value=["case_one", "case_three"],
            invalid_values=["case_three"]
        ),
        lambda: loader(["case_one", "case_three"])
    )


def test_flag_enum_dumper_with_disallowed_compounds(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(NameEnumMappingGenerator(), allow_compound=False),
        ]
    )

    dumper = retort.get_dumper(FlagEnum)
    assert dumper(FlagEnum.case_one) == ["case_one"]
    assert dumper(FlagEnum.case_one | FlagEnum.case_two) == ["case_one", "case_two"]
    assert dumper(FlagEnum.case_three) == ["case_one", "case_two"]


def test_flag_enum_loader_with_allowed_single_value(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(NameEnumMappingGenerator(), allow_single_value=True),
        ]
    )

    loader = retort.get_loader(FlagEnum)
    assert loader("case_one") == FlagEnum.case_one
    assert loader("case_three") == FlagEnum.case_three


def test_flag_enum_loader_with_disallowed_duplicates(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(NameEnumMappingGenerator(), allow_duplicates=False),
        ]
    )

    loader = retort.get_loader(FlagEnum)
    raises_exc(
        ValueLoadError(
            f"Duplicates in {FlagEnum} loader are not allowed",
            ["case_one", "case_one"]
        ),
        lambda: loader(["case_one", "case_one"])
    )


def test_flag_enum_loader_with_name_mapping(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(
                NameEnumMappingGenerator(
                    name_style=NameStyle.CAMEL,
                    map={
                        "case_one": "case_1",
                        #  maps given by cases have higher priority that
                        #  ones given by names
                        FlagEnum.case_one: "caseFirst",
                        "case_two": "caseSecond",
                        "ignore": "ignore"
                    }
                ),
            ),
        ]
    )

    loader = retort.get_loader(FlagEnum)
    assert loader(["caseFirst"]) == FlagEnum.case_one
    assert loader(["caseFirst", "caseSecond"]) == FlagEnum.case_three
    assert loader(["caseThree"]) == FlagEnum.case_three

    variants = ["caseFirst", "caseSecond", "caseThree", "caseFour", "caseEight"]
    raises_exc(
        MultipleBadVariant(
            allowed_values=variants,
            input_value=["caseThree", "case_two", "case_1"],
            invalid_values=["case_two", "case_1"]
        ),
        lambda: loader(["caseThree", "case_two", "case_1"])
    )


def test_flag_enum_dumper_with_name_mapping(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(
                NameEnumMappingGenerator(
                    name_style=NameStyle.CAMEL,
                    map={
                        "case_one": "case_1",
                        #  maps given by cases themselves have higher priority that
                        #  ones given by their names
                        FlagEnum.case_one: "caseFirst",
                        "case_two": "caseSecond",
                        "ignore": "ignore"
                    }
                ),
            ),
        ]
    )

    dumper = retort.get_dumper(FlagEnum)
    assert dumper(FlagEnum.case_one) == ["caseFirst"]
    assert dumper(FlagEnum.case_two) == ["caseSecond"]
    assert dumper(FlagEnum.case_one | FlagEnum.case_two) == ["caseThree"]
