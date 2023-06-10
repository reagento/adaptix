import pytest

from adaptix._internal.model_tools.definitions import (
    InputField,
    InputShape,
    NoDefault,
    OutputField,
    OutputShape,
    ParamKind,
    create_attr_accessor,
)


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
    with pytest.raises(ValueError):
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
                    param_kind=first,
                    param_name='a',
                ),
                InputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=second,
                    param_name='a',
                ),
            ),
            overriden_types=frozenset({'a'}),
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
                param_kind=first,
                param_name='a',
            ),
            InputField(
                id="b",
                type=int,
                default=NoDefault(),
                is_required=False,
                metadata={},
                param_kind=second,
                param_name='b',
            ),
            InputField(
                id="c",
                type=int,
                default=NoDefault(),
                is_required=True,
                metadata={},
                param_kind=third,
                param_name='c',
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


def test_name_duplicates():
    with pytest.raises(ValueError):
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
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a1',
                ),
                InputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a2',
                ),
            ),
            overriden_types=frozenset({'a'}),
        )

    with pytest.raises(ValueError):
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
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
                InputField(
                    id="a2",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
            ),
            overriden_types=frozenset({'a1', 'a2'}),
        )

    with pytest.raises(ValueError):
        OutputShape(
            fields=(
                OutputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    accessor=create_attr_accessor("a", is_required=True),
                    metadata={},
                ),
                OutputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    accessor=create_attr_accessor("a", is_required=True),
                    metadata={},
                ),
            ),
            overriden_types=frozenset({'a'}),
        )


def test_optional_and_positional_only():
    with pytest.raises(ValueError):
        InputField(
            id="a",
            type=int,
            default=NoDefault(),
            is_required=False,
            metadata={},
            param_kind=ParamKind.POS_ONLY,
            param_name='a',
        )


def test_non_existing_fields_overriden_types():
    with pytest.raises(ValueError):
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
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
                InputField(
                    id="b",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='b',
                ),
            ),
            overriden_types=frozenset({'c'}),
        )

    with pytest.raises(ValueError):
        OutputShape(
            fields=(
                OutputField(
                    id="a",
                    type=int,
                    default=NoDefault(),
                    accessor=create_attr_accessor("a", is_required=True),
                    metadata={},
                ),
                OutputField(
                    id="b",
                    type=int,
                    default=NoDefault(),
                    accessor=create_attr_accessor("b", is_required=True),
                    metadata={},
                ),
            ),
            overriden_types=frozenset({'c'}),
        )
