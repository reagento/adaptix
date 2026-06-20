import re

import pytest

from adaptix._internal.morphing.json_schema.definitions import JSONSchema
from adaptix._internal.morphing.json_schema.ref_generator import BuiltinRefGenerator
from adaptix._internal.provider.loc_stack_filtering import LocStack
from adaptix._internal.provider.location import TypeHintLoc

generator = BuiltinRefGenerator()


def ref_for(tp):
    return generator.generate_ref(JSONSchema(), LocStack(TypeHintLoc(tp)))


class _SimpleModel:
    pass


class _OuterModel:
    class _InnerModel:
        pass


@pytest.mark.parametrize(
    ["tp", "expected"],
    [
        (int, "int"),
        (str, "str"),
        (float, "float"),
        (bool, "bool"),
        (bytes, "bytes"),
    ],
)
def test_builtin_type_ref(tp, expected):
    assert ref_for(tp) == expected


def test_simple_class_uses_qualname():
    assert ref_for(_SimpleModel) == "_SimpleModel"


def test_nested_class_uses_full_qualname():
    assert ref_for(_OuterModel._InnerModel) == "_OuterModel._InnerModel"


@pytest.mark.parametrize(
    ["tp", "expected"],
    [
        (list[int], "list_int"),
        (dict[str, int], "dict_str_int"),
        (list[dict[str, list[int]]], "list_dict_str_list_int"),
    ],
)
def test_generic_type_ref_replaces_unsafe_chars_with_underscores(tp, expected):
    assert ref_for(tp) == expected


URI_SAFE_PATTERN = re.compile(r"[A-Za-z0-9\-._~]+")


@pytest.mark.parametrize(
    "tp",
    [list[int], dict[str, int], list[dict[str, list[int]]]],
)
def test_generic_type_ref_contains_only_uri_safe_chars(tp):
    result = ref_for(tp)

    assert URI_SAFE_PATTERN.fullmatch(result)
