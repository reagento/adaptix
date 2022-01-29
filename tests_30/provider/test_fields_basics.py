import pytest

from dataclass_factory_30.provider import NoDefault
from dataclass_factory_30.provider.fields_basics import InputFieldsFigure, InputFieldRM, ExtraTargets
from dataclass_factory_30.provider.request_cls import ParamKind


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
        InputFieldsFigure(
            extra=None,
            fields=[
                InputFieldRM(
                    field_name="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=first,
                ),
                InputFieldRM(
                    field_name="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=second,
                ),
            ],
        )


def _make_triple_iff(first, second, third):
    return InputFieldsFigure(
        extra=None,
        fields=[
            InputFieldRM(
                field_name="a",
                type=int,
                default=NoDefault(),
                is_required=True,
                metadata={},
                param_kind=first,
            ),
            InputFieldRM(
                field_name="b",
                type=int,
                default=NoDefault(),
                is_required=False,
                metadata={},
                param_kind=second,
            ),
            InputFieldRM(
                field_name="c",
                type=int,
                default=NoDefault(),
                is_required=True,
                metadata={},
                param_kind=third,
            ),
        ],
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


def test_field_name_duplicates():
    with pytest.raises(ValueError):
        InputFieldsFigure(
            extra=None,
            fields=[
                InputFieldRM(
                    field_name="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                ),
                InputFieldRM(
                    field_name="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                ),
            ]
        )


def test_wild_targets():
    with pytest.raises(ValueError):
        InputFieldsFigure(
            extra=ExtraTargets(["b"]),
            fields=[
                InputFieldRM(
                    field_name="a",
                    type=int,
                    default=NoDefault(),
                    is_required=True,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                ),
            ]
        )
