from enum import Enum, Flag, IntEnum, auto
from typing import Iterable

import pytest
from tests_helpers import TestRetort, raises_exc

from adaptix import dumper, enum_by_value, loader
from adaptix._internal.morphing.enum_provider import EnumExactValueProvider, EnumNameProvider, FlagProvider
from adaptix._internal.morphing.load_error import MultipleBadVariantError, TypeLoadError, ValueLoadError
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
    V1 = auto()
    V2 = auto()
    V3 = auto()
    V5 = V2 | V3
    V6 = V1 | V2 | V3


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
    assert EnumExactValueProvider()._make_loader(
        MyEnum).__name__ == 'enum_exact_loader_v2m'
    assert EnumExactValueProvider()._make_loader(
        MyEnumWithMissingHook).__name__ == 'enum_exact_loader'


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
            FlagProvider(),
        ]
    )

    loader = retort.get_loader(FlagEnum)
    assert loader(["V1"]) == FlagEnum.V1
    assert loader(["V1", "V2", "V3"]) == FlagEnum.V6
    assert loader(["V6"]) == FlagEnum.V6
    assert loader(["V2", "V3"]) == FlagEnum.V5
    assert loader(["V1", "V2"]) == FlagEnum.V1 | FlagEnum.V2
    assert loader(["V1", "V1"]) == FlagEnum.V1

    variants = ["V1", "V2", "V3", "V5", "V6"]
    raises_exc(
        MultipleBadVariantError(
            allowed_values=variants,
            input_values=["V7", "V8", "V6"],
            invalid_values=["V7", "V8"]
        ),
        lambda: loader(["V7", "V8", "V6"])
    )
    raises_exc(
        TypeLoadError(
            expected_type=Iterable[str],
            input_value="V1"
        ),
        lambda: loader("V1")
    )


def test_flag_enum_dumper(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(),
        ]
    )

    dumper = retort.get_dumper(FlagEnum)
    assert dumper(FlagEnum.V1) == ["V1"]
    assert dumper(FlagEnum.V1 | FlagEnum.V2 | FlagEnum.V3) == ["V6"]
    assert dumper(FlagEnum.V1 | FlagEnum.V2) == ["V1", "V2"]
    assert dumper(FlagEnum.V1 & FlagEnum.V2) == []
    assert dumper(FlagEnum.V2 & FlagEnum.V5) == ["V2"]
    assert dumper(~FlagEnum.V2) == ["V1", "V3"]


def test_flag_enum_loader_by_exact_value(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(by_exact_value=True),
        ]
    )

    loader = retort.get_loader(FlagEnum)
    assert loader([1]) == FlagEnum.V1
    assert loader([1, 2, 4]) == FlagEnum.V6
    assert loader([7]) == FlagEnum.V6
    assert loader([2, 4]) == FlagEnum.V5
    assert loader([1, 2]) == FlagEnum.V1 | FlagEnum.V2
    variants = [1, 2, 4, 6, 7]
    raises_exc(
        MultipleBadVariantError(
            allowed_values=variants,
            input_values=[3, 5, 7],
            invalid_values=[3, 5]
        ),
        lambda: loader([3, 5, 7])
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
            FlagProvider(by_exact_value=True),
        ]
    )

    dumper = retort.get_dumper(FlagEnum)
    assert dumper(FlagEnum.V1) == [1]
    assert dumper(FlagEnum.V1 | FlagEnum.V2 | FlagEnum.V3) == [7]
    assert dumper(FlagEnum.V1 | FlagEnum.V2) == [1, 2]
    assert dumper(FlagEnum.V1 & FlagEnum.V2) == []
    assert dumper(FlagEnum.V2 & FlagEnum.V5) == [2]
    assert dumper(~FlagEnum.V2) == [1, 4]


def test_flag_enum_loader_with_disallowed_compounds(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(allow_compound=False),
        ]
    )

    loader = retort.get_loader(FlagEnum)
    assert loader(["V1"]) == FlagEnum.V1
    assert loader(["V1", "V2", "V3"]) == FlagEnum.V6
    assert loader(["V1", "V2"]) == FlagEnum.V1 | FlagEnum.V2

    variants = ["V1", "V2", "V3"]
    raises_exc(
        MultipleBadVariantError(
            allowed_values=variants,
            input_values=["V1", "V6"],
            invalid_values=["V6"]
        ),
        lambda: loader(["V1", "V6"])
    )


def test_flag_enum_dumper_with_disallowed_compounds(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(allow_compound=False),
        ]
    )

    dumper = retort.get_dumper(FlagEnum)
    assert dumper(FlagEnum.V1) == ["V1"]
    assert dumper(FlagEnum.V1 | FlagEnum.V2 | FlagEnum.V3) == ["V1", "V2", "V3"]
    assert dumper(FlagEnum.V1 | FlagEnum.V2) == ["V1", "V2"]
    assert dumper(FlagEnum.V1 & FlagEnum.V2) == []
    assert dumper(FlagEnum.V2 & FlagEnum.V5) == ["V2"]
    assert dumper(~FlagEnum.V2) == ["V1", "V3"]


def test_flag_enum_loader_with_allowed_single_value(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(allow_single_value=True),
        ]
    )

    loader = retort.get_loader(FlagEnum)
    assert loader("V1") == FlagEnum.V1
    assert loader("V5") == FlagEnum.V5


def test_flag_enum_loader_with_disallowed_duplicates(strict_coercion, debug_trail):
    retort = TestRetort(
        strict_coercion=strict_coercion,
        debug_trail=debug_trail,
        recipe=[
            FlagProvider(allow_duplicates=False),
        ]
    )

    loader = retort.get_loader(FlagEnum)
    raises_exc(
        ValueLoadError(f"Duplicates in {FlagEnum} loader are not allowed", ["V1", "V1"]),
        lambda: loader(["V1", "V1"])
    )
