import pytest

from adaptix._internal.model_tools.definitions import (
    InputField,
    InputShape,
    NoDefault,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    create_attr_accessor,
)
from tests_helpers import full_match_regex_str


def stub_constructor(*args, **kwargs):
    pass


@pytest.mark.parametrize(
    ["first", "second"],
    [
        (ParamKind.KW_ONLY, ParamKind.POS_ONLY),
        (ParamKind.KW_ONLY, ParamKind.POS_OR_KW),
        (ParamKind.POS_OR_KW, ParamKind.POS_ONLY),
    ]
)
def test_inconsistent_fields_order(first, second):
    with pytest.raises(
        ValueError,
        match='^Inconsistent order of fields.*',
    ):
        InputShape(
            constructor=stub_constructor,
            kwargs=None,
            fields=(
                InputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    original=None,
                ),
                InputField(
                    id="b",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    original=None,
                ),
            ),
            params=(
                Param(
                    field_id='a',
                    name='a',
                    kind=first,
                ),
                Param(
                    field_id='b',
                    name='b',
                    kind=second,
                ),
            ),
            overriden_types=frozenset({'a', 'b'}),
        )


def _make_triple_iff(first, second, third):
    return InputShape(
        constructor=stub_constructor,
        kwargs=None,
        fields=(
            InputField(
                id="a",
                type=int,
                default=NoDefault(),
                is_required=True,
                metadata={},
                original=None,
            ),
            InputField(
                id="b",
                type=int,
                default=NoDefault(),
                is_required=False,
                metadata={},
                original=None,
            ),
            InputField(
                id="c",
                type=int,
                default=NoDefault(),
                is_required=True,
                metadata={},
                original=None,
            ),
        ),
        params=(
            Param(
                field_id='a',
                name='a',
                kind=first,
            ),
            Param(
                field_id='b',
                name='b',
                kind=second,
            ),
            Param(
                field_id='c',
                name='c',
                kind=third,
            ),
        ),
        overriden_types=frozenset({'a', 'b', 'c'}),
    )


@pytest.mark.parametrize(
    ["first", "second", "third"],
    [
        (ParamKind.POS_ONLY, ParamKind.POS_OR_KW, ParamKind.POS_OR_KW),
        (ParamKind.POS_OR_KW, ParamKind.POS_OR_KW, ParamKind.POS_OR_KW),
    ]
)
def test_bad_non_required_field_order(first, second, third):
    with pytest.raises(ValueError):
        _make_triple_iff(first, second, third)


@pytest.mark.parametrize(
    ["first", "second", "third"],
    [
        (ParamKind.POS_ONLY, ParamKind.POS_OR_KW, ParamKind.KW_ONLY),
        (ParamKind.POS_OR_KW, ParamKind.POS_OR_KW, ParamKind.KW_ONLY),
        (ParamKind.POS_ONLY, ParamKind.KW_ONLY, ParamKind.KW_ONLY),
        (ParamKind.POS_OR_KW, ParamKind.KW_ONLY, ParamKind.KW_ONLY),
    ]
)
def test_ok_non_required_field_order(first, second, third):
    _make_triple_iff(first, second, third)


def test_field_id_duplicates():
    with pytest.raises(ValueError, match=full_match_regex_str("Field ids {'a'} are duplicated")):
        InputShape(
            constructor=stub_constructor,
            kwargs=None,
            fields=(
                InputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    original=None,
                ),
                InputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    original=None,
                ),
            ),
            params=(
                Param(
                    field_id='a',
                    name='a1',
                    kind=ParamKind.POS_OR_KW,
                ),
                Param(
                    field_id='a',
                    name='a2',
                    kind=ParamKind.POS_OR_KW,
                ),
            ),
            overriden_types=frozenset({'a'}),
        )

    with pytest.raises(ValueError, match=full_match_regex_str("Field ids {'a'} are duplicated")):
        OutputShape(
            fields=(
                OutputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    accessor=create_attr_accessor("a", is_required=True),
                    metadata={},
                    original=None,
                ),
                OutputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    accessor=create_attr_accessor("a", is_required=True),
                    metadata={},
                    original=None,
                ),
            ),
            overriden_types=frozenset({'a'}),
        )


def test_param_name_duplicates():
    with pytest.raises(ValueError, match=full_match_regex_str("Parameter names {'a'} are duplicated")):
        InputShape(
            constructor=stub_constructor,
            kwargs=None,
            fields=(
                InputField(
                    id="a1",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    original=None,
                ),
                InputField(
                    id="a2",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    original=None,
                ),
            ),
            params=(
                Param(
                    field_id='a1',
                    name='a',
                    kind=ParamKind.POS_OR_KW,
                ),
                Param(
                    field_id='a2',
                    name='a',
                    kind=ParamKind.POS_OR_KW,
                )
            ),
            overriden_types=frozenset({'a1', 'a2'}),
        )


def test_optional_and_positional_only():
    with pytest.raises(ValueError, match=full_match_regex_str("Field 'a' can not be positional only and optional")):
        InputShape(
            constructor=stub_constructor,
            kwargs=None,
            fields=(
                InputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    is_required=False,
                    metadata={},
                    original=None,
                ),
            ),
            params=(
                Param(
                    field_id='a',
                    name='a',
                    kind=ParamKind.POS_ONLY,
                ),
            ),
            overriden_types=frozenset({'a'}),
        )


def test_non_existing_fields_overriden_types():
    with pytest.raises(
        ValueError,
        match=full_match_regex_str("overriden_types contains non existing fields frozenset({'c'})"),
    ):
        InputShape(
            constructor=stub_constructor,
            kwargs=None,
            fields=(
                InputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    original=None,
                ),
                InputField(
                    id="b",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    original=None,
                ),
            ),
            params=(
                Param(
                    field_id='a',
                    name='a',
                    kind=ParamKind.POS_OR_KW,
                ),
                Param(
                    field_id='b',
                    name='b',
                    kind=ParamKind.POS_OR_KW,
                ),
            ),
            overriden_types=frozenset({'c'}),
        )

    with pytest.raises(
        ValueError,
        match=full_match_regex_str("overriden_types contains non existing fields frozenset({'c'})"),
    ):
        OutputShape(
            fields=(
                OutputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    accessor=create_attr_accessor("a", is_required=True),
                    metadata={},
                    original=None,
                ),
                OutputField(
                    id="b",
                    type=int,
                    default=NoDefault(),
                    accessor=create_attr_accessor("b", is_required=True),
                    metadata={},
                    original=None,
                ),
            ),
            overriden_types=frozenset({'c'}),
        )


def test_parameter_bound_to_non_existing_field():
    with pytest.raises(
        ValueError,
        match=full_match_regex_str("Parameters {'b': 'b'} bind to non-existing fields"),
    ):
        InputShape(
            constructor=stub_constructor,
            kwargs=None,
            fields=(
                InputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    original=None,
                ),
            ),
            params=(
                Param(
                    field_id='a',
                    name='a',
                    kind=ParamKind.POS_OR_KW,
                ),
                Param(
                    field_id='b',
                    name='b',
                    kind=ParamKind.POS_OR_KW,
                ),
            ),
            overriden_types=frozenset({'a'}),
        )


def test_field_without_parameters():
    with pytest.raises(
        ValueError,
        match=full_match_regex_str("Fields {'a'} do not bound to any parameter"),
    ):
        InputShape(
            constructor=stub_constructor,
            kwargs=None,
            fields=(
                InputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    original=None,
                ),
            ),
            params=(),
            overriden_types=frozenset({'a'}),
        )
