import pytest

from dataclass_factory_30.model_tools import (
    AttrAccessor,
    ExtraTargets,
    InputField,
    InputFigure,
    NoDefault,
    OutputField,
    OutputFigure,
    ParamKind
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
        InputFigure(
            constructor=stub_constructor,
            extra=None,
            fields=(
                InputField(
                    name="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=first,
                    param_name='a',
                ),
                InputField(
                    name="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=second,
                    param_name='a',
                ),
            ),
        )


def _make_triple_iff(first, second, third):
    return InputFigure(
        constructor=stub_constructor,
        extra=None,
        fields=(
            InputField(
                name="a",
                type=int,
                default=NoDefault(),
                is_required=True,
                metadata={},
                param_kind=first,
                param_name='a',
            ),
            InputField(
                name="b",
                type=int,
                default=NoDefault(),
                is_required=False,
                metadata={},
                param_kind=second,
                param_name='b',
            ),
            InputField(
                name="c",
                type=int,
                default=NoDefault(),
                is_required=True,
                metadata={},
                param_kind=third,
                param_name='c',
            ),
        ),
    )


@pytest.mark.parametrize(
    ["first", "second", "third"],
    [
        (ParamKind.POS_ONLY, ParamKind.POS_ONLY, ParamKind.POS_ONLY),
        (ParamKind.POS_ONLY, ParamKind.POS_ONLY, ParamKind.POS_OR_KW),
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
        (ParamKind.POS_ONLY, ParamKind.POS_ONLY, ParamKind.KW_ONLY),
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
        InputFigure(
            constructor=stub_constructor,
            extra=None,
            fields=(
                InputField(
                    name="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a1',
                ),
                InputField(
                    name="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a2',
                ),
            )
        )

    with pytest.raises(ValueError):
        InputFigure(
            constructor=stub_constructor,
            extra=None,
            fields=(
                InputField(
                    name="a1",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
                InputField(
                    name="a2",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
            )
        )

    with pytest.raises(ValueError):
        OutputFigure(
            extra=None,
            fields=(
                OutputField(
                    name="a",
                    type=int,
                    default=NoDefault(),
                    accessor=AttrAccessor("a", is_required=True),
                    metadata={},
                ),
                OutputField(
                    name="a",
                    type=int,
                    default=NoDefault(),
                    accessor=AttrAccessor("a", is_required=True),
                    metadata={},
                ),
            )
        )


def test_wild_targets():
    with pytest.raises(ValueError):
        InputFigure(
            constructor=stub_constructor,
            extra=ExtraTargets(("b",)),
            fields=(
                InputField(
                    name="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                    param_name='a',
                ),
            )
        )

    with pytest.raises(ValueError):
        OutputFigure(
            extra=ExtraTargets(("b",)),
            fields=(
                OutputField(
                    name="a",
                    type=int,
                    default=NoDefault(),
                    accessor=AttrAccessor("a", is_required=True),
                    metadata={},
                ),
            )
        )
