from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum, Flag, IntEnum, auto
from typing import Union

import pytest
from tests_helpers import parametrize_bool, raises_exc
from tests_helpers.misc import raises_exc_text

from adaptix import DebugTrail, NameStyle, Retort, dumper, enum_by_name, enum_by_value, flag_by_member_names
from adaptix._internal.morphing.load_error import (
    DuplicatedValuesLoadError,
    ExcludedTypeLoadError,
    MultipleBadVariantLoadError,
    OutOfRangeLoadError,
    TypeLoadError,
)
from adaptix.load_error import BadVariantLoadError, MsgLoadError


class MyEnum(Enum):
    V1 = "1"


class MyIntEnum(IntEnum):
    V1 = 1


class MyEnumWithMissingHook(Enum):
    V1 = "1"

    @classmethod
    def _missing_(cls, value: object) -> "MyEnumWithMissingHook":
        raise ValueError


class FlagEnum(Flag):
    CASE_ONE = auto()
    CASE_TWO = auto()
    CASE_THREE = CASE_ONE | CASE_TWO
    CASE_FOUR = auto()
    CASE_EIGHT = auto()


class FlagEnumWithSkippedBit(Flag):
    CASE_ONE = 1
    CASE_FOUR = 4


class FlagEnumWithNegativeValue(Flag):
    CASE_ONE = -1


def test_name_provider(strict_coercion, debug_trail):
    retort = Retort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            enum_by_name(),
        ],
    )

    loader = retort.get_loader(MyEnum)
    assert loader("V1") == MyEnum.V1

    raises_exc(
        BadVariantLoadError(["V1"], "1"),
        lambda: loader("1"),
    )

    raises_exc(
        BadVariantLoadError(["V1"], 1),
        lambda: loader(1),
    )

    raises_exc(
        BadVariantLoadError(["V1"], MyEnum.V1),
        lambda: loader(MyEnum.V1),
    )

    dumper = retort.get_dumper(MyEnum)

    assert dumper(MyEnum.V1) == "V1"


@pytest.mark.parametrize("mapping_options", [{"name_style": NameStyle.CAMEL}, {"map": {"V1": "v1"}}])
def test_name_provider_with_mapping(strict_coercion, debug_trail, mapping_options):
    retort = Retort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            enum_by_name(**mapping_options),
        ],
    )

    loader = retort.get_loader(MyEnum)
    assert loader("v1") == MyEnum.V1

    raises_exc(
        BadVariantLoadError(["v1"], "V1"),
        lambda: loader("V1"),
    )

    dumper = retort.get_dumper(MyEnum)
    assert dumper(MyEnum.V1) == "v1"


@pytest.mark.parametrize("enum_cls", [MyEnum, MyEnumWithMissingHook])
def test_exact_value_provider(strict_coercion, debug_trail, enum_cls):
    retort = Retort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    )

    loader = retort.get_loader(enum_cls)

    assert loader("1") == enum_cls.V1

    raises_exc(
        BadVariantLoadError(["1"], "V1"),
        lambda: loader("V1"),
    )

    raises_exc(
        BadVariantLoadError(["1"], 1),
        lambda: loader(1),
    )

    raises_exc(
        BadVariantLoadError(["1"], enum_cls.V1),
        lambda: loader(enum_cls.V1),
    )

    dumper = retort.get_dumper(enum_cls)

    assert dumper(enum_cls.V1) == "1"


def test_exact_value_provider_int_enum(strict_coercion, debug_trail):
    retort = Retort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    )
    int_enum_loader = retort.get_loader(MyIntEnum)

    assert int_enum_loader(1) == MyIntEnum.V1

    raises_exc(
        BadVariantLoadError([1], MyEnum.V1),
        lambda: int_enum_loader(MyEnum.V1),
    )

    raises_exc(
        BadVariantLoadError([1], "V1"),
        lambda: int_enum_loader("V1"),
    )


def test_exact_value_optimization(strict_coercion):
    retort = Retort(
        strict_coercion=strict_coercion,
        debug_trail=DebugTrail.DISABLE,
    )
    assert retort.get_loader(MyEnum).__name__ == "enum_exact_loader_v2m"
    assert retort.get_loader(MyEnumWithMissingHook).__name__ == "enum_exact_loader"


def custom_string_dumper(value: str):
    return "PREFIX " + value


def test_value_provider(strict_coercion, debug_trail):
    retort = Retort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            enum_by_value(MyEnum, tp=str),
            dumper(str, custom_string_dumper),
        ],
    )

    enum_loader = retort.get_loader(MyEnum)

    assert enum_loader("1") == MyEnum.V1

    if not strict_coercion:
        assert enum_loader(1) == MyEnum.V1

        raises_exc(
            MsgLoadError("Bad enum value", MyEnum.V1),
            lambda: enum_loader(MyEnum.V1),
        )

    raises_exc(
        MsgLoadError("Bad enum value", "V1"),
        lambda: enum_loader("V1"),
    )

    enum_dumper = retort.get_dumper(MyEnum)

    assert enum_dumper(MyEnum.V1) == "PREFIX 1"


def test_flag_by_exact_value(strict_coercion, debug_trail):
    retort = Retort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    )

    loader = retort.get_loader(FlagEnum)
    assert loader(1) == FlagEnum.CASE_ONE
    assert loader(3) == FlagEnum.CASE_THREE
    assert loader(5) == FlagEnum.CASE_ONE | FlagEnum.CASE_FOUR

    dumper = retort.get_dumper(FlagEnum)
    assert dumper(FlagEnum.CASE_ONE) == 1
    assert dumper(FlagEnum.CASE_ONE | FlagEnum.CASE_FOUR) == 5

    raises_exc(
        OutOfRangeLoadError(0, 15, 16), lambda: loader(16),
    )
    raises_exc(
        OutOfRangeLoadError(0, 15, -1), lambda: loader(-1),
    )


@pytest.mark.parametrize("data", [{"data": 1}, "1", [1], None])
def test_flag_by_exact_value_loader_with_bad_types(strict_coercion, debug_trail, data):
    retort = Retort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    )
    loader = retort.get_loader(FlagEnum)
    raises_exc(TypeLoadError(int, data), lambda: loader(data))


def test_flag_by_exact_value_loader_creation_fail(strict_coercion, debug_trail):
    retort = Retort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
    )

    @dataclass
    class SomeClass:
        field: FlagEnumWithNegativeValue

    raises_exc_text(
        lambda: retort.get_loader(SomeClass),
        """
        adaptix.ProviderNotFoundError: Cannot produce loader for type <class '__main__.SomeClass'>
          × Cannot create loader for model. Loaders for some fields cannot be created
          │ Location: ‹SomeClass›
          ╰──▷ Cannot create a loader for flag with negative values
               Location: ‹SomeClass.field: FlagEnumWithNegativeValue›
        """,
        {
            "SomeClass": SomeClass.__qualname__,
            "__main__": __name__,
        },
    )


@parametrize_bool("allow_single_value", "allow_duplicates", "allow_compound")
def test_flag_by_member_names(
    strict_coercion, debug_trail, allow_single_value, allow_duplicates, allow_compound,
):
    retort = Retort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            flag_by_member_names(
                allow_single_value=allow_single_value,
                allow_duplicates=allow_duplicates,
                allow_compound=allow_compound,
            ),
        ],
    )

    loader = retort.get_loader(FlagEnum)
    assert loader(["CASE_ONE"]) == FlagEnum.CASE_ONE
    assert loader(["CASE_ONE", "CASE_TWO"]) == FlagEnum.CASE_THREE
    assert loader(["CASE_ONE", "CASE_FOUR"]) == FlagEnum.CASE_ONE | FlagEnum.CASE_FOUR

    if allow_compound:
        variants = ["CASE_ONE", "CASE_TWO", "CASE_THREE", "CASE_FOUR", "CASE_EIGHT"]
    else:
        variants = ["CASE_ONE", "CASE_TWO", "CASE_FOUR", "CASE_EIGHT"]

    raises_exc(
        MultipleBadVariantLoadError(
            allowed_values=variants,
            invalid_values=["NOT_EXISTING_CASE_1", "NOT_EXISTING_CASE_2"],
            input_value=["CASE_ONE", "NOT_EXISTING_CASE_1", "NOT_EXISTING_CASE_2"],
        ),
        lambda: loader(["CASE_ONE", "NOT_EXISTING_CASE_1", "NOT_EXISTING_CASE_2"]),
    )

    data_with_compound = ["CASE_THREE"]
    if allow_compound:
        assert loader(data_with_compound) == FlagEnum.CASE_THREE
    else:
        raises_exc(
            MultipleBadVariantLoadError(variants, ["CASE_THREE"], data_with_compound),
            lambda: loader(data_with_compound),
        )

    data_with_duplicates = ["CASE_ONE", "CASE_ONE"]
    if allow_duplicates:
        assert loader(data_with_duplicates) == FlagEnum.CASE_ONE
    else:
        raises_exc(
            DuplicatedValuesLoadError(data_with_duplicates),
            lambda: loader(data_with_duplicates),
        )

    dumper = retort.get_dumper(FlagEnum)
    assert dumper(FlagEnum.CASE_ONE) == ["CASE_ONE"]
    assert dumper(FlagEnum.CASE_ONE & FlagEnum.CASE_TWO) == []
    assert dumper(~FlagEnum.CASE_TWO) == ["CASE_ONE", "CASE_FOUR", "CASE_EIGHT"]

    compound = FlagEnum.CASE_THREE
    compound_with_non_compound = FlagEnum.CASE_FOUR | FlagEnum.CASE_THREE
    if allow_compound:
        assert dumper(compound) == ["CASE_THREE"]
        assert dumper(compound_with_non_compound) == ["CASE_THREE", "CASE_FOUR"]
    else:
        assert dumper(compound) == ["CASE_ONE", "CASE_TWO"]
        assert dumper(compound_with_non_compound) == ["CASE_ONE", "CASE_TWO", "CASE_FOUR"]


@parametrize_bool("allow_single_value", "allow_duplicates", "allow_compound")
def test_flag_by_member_names_with_bad_types(
    strict_coercion, debug_trail, allow_single_value, allow_duplicates, allow_compound,
):
    retort = Retort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            flag_by_member_names(
                allow_single_value=allow_single_value,
                allow_duplicates=allow_duplicates,
                allow_compound=allow_compound,
            ),
        ],
    )

    loader = retort.get_loader(FlagEnum)
    expected_type = Union[str, Iterable[str]] if allow_single_value else Iterable[str]

    dict_data = {"CASE_ONE": 1}
    if strict_coercion:
        raises_exc(
            ExcludedTypeLoadError(expected_type, Mapping, dict_data),
            lambda: loader(dict_data),
        )
    else:
        assert loader(dict_data) == FlagEnum.CASE_ONE

    str_data = "CASE_ONE"
    if allow_single_value:
        assert loader(str_data) == loader([str_data])
    else:
        raises_exc(
            TypeLoadError(expected_type, str_data),
            lambda: loader(str_data),
        )

    raises_exc(
        TypeLoadError(expected_type, 1),
        lambda: loader(1),
    )
    raises_exc(
        TypeLoadError(expected_type, None),
        lambda: loader(None),
    )


def test_flag_by_member_names_with_mapping(strict_coercion, debug_trail):
    retort = Retort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            flag_by_member_names(
                name_style=NameStyle.CAMEL,
                map={
                    "CASE_ONE": "CASE_1",
                    #  maps given by cases have higher priority that
                    #  ones given by names.
                    FlagEnum.CASE_ONE: "caseFirst",
                    "CASE_TWO": "caseSecond",
                    "ignore": "ignore",
                },
            ),
        ],
    )

    loader = retort.get_loader(FlagEnum)
    assert loader(["caseFirst"]) == FlagEnum.CASE_ONE
    assert loader(["caseFirst", "caseSecond"]) == FlagEnum.CASE_THREE
    assert loader(["caseThree"]) == FlagEnum.CASE_THREE

    variants = ["caseFirst", "caseSecond", "caseThree", "caseFour", "caseEight"]
    raises_exc(
        MultipleBadVariantLoadError(
            allowed_values=variants,
            input_value=["caseThree", "CASE_TWO", "CASE_1"],
            invalid_values=["CASE_TWO", "CASE_1"],
        ),
        lambda: loader(["caseThree", "CASE_TWO", "CASE_1"]),
    )

    dumper = retort.get_dumper(FlagEnum)
    assert dumper(FlagEnum.CASE_ONE) == ["caseFirst"]
    assert dumper(FlagEnum.CASE_TWO) == ["caseSecond"]
    assert dumper(FlagEnum.CASE_ONE | FlagEnum.CASE_TWO) == ["caseThree"]
