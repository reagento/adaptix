import pytest

from dataclass_factory_30.model_tools import (
    ParamKind, InputFigure, InputField,
    NoDefault, OutputFigure, OutputField,
    AttrAccessor, ExtraTargets
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
                ),
                InputField(
                    name="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=second,
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
            ),
            InputField(
                name="b",
                type=int,
                default=NoDefault(),
                is_required=False,
                metadata={},
                param_kind=second,
            ),
            InputField(
                name="c",
                type=int,
                default=NoDefault(),
                is_required=True,
                metadata={},
                param_kind=third,
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
                ),
                InputField(
                    name="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
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
