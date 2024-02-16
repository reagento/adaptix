import typing
import warnings
from types import MappingProxyType
from typing import AbstractSet, Sequence, Set, Tuple

from ...feature_requirement import HAS_PY_39, HAS_TYPED_DICT_REQUIRED
from ...type_tools import BaseNormType, get_all_type_hints, is_typed_dict_class, normalize_type
from ..definitions import (
    FullShape,
    InputField,
    InputShape,
    IntrospectionImpossible,
    NoDefault,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    Shape,
    create_key_accessor,
)


class TypedDictAt38Warning(UserWarning):
    """Runtime introspection of TypedDict at python3.8 does not support inheritance.
    Please update python or consider limitations suppressing this warning
    """

    def __str__(self):
        return (
            "Runtime introspection of TypedDict at python3.8 does not support inheritance."
            " Please, update python or consider limitations suppressing this warning"
        )


def _get_td_hints(tp):
    elements = list(get_all_type_hints(tp).items())
    elements.sort(key=lambda v: v[0])
    return elements


def _extract_item_type(tp) -> BaseNormType:
    if tp.origin is typing.Annotated:
        return tp.args[0]
    return tp


def _fetch_required_keys(
    fields: Sequence[Tuple[str, BaseNormType]],
    frozen_required_keys: AbstractSet[str],
) -> Set:
    required_keys = set(frozen_required_keys)

    for field_name, field_tp in fields:
        require_type = _extract_item_type(field_tp)
        if require_type.origin is typing.Required and field_name not in required_keys:
            required_keys.add(field_name)
        elif require_type.origin is typing.NotRequired and field_name in required_keys:
            required_keys.remove(field_name)

    return required_keys


def _make_requirement_determinant_from_keys(required_fields: set):
    return lambda name: name in required_fields


if HAS_PY_39:
    def _make_requirement_determinant_from_type(tp):
        required_fields = tp.__required_keys__
        return lambda name: name in required_fields
else:
    def _make_requirement_determinant_from_type(tp):
        warnings.warn(TypedDictAt38Warning(), stacklevel=3)
        is_total = tp.__total__
        return lambda name: is_total


def get_typed_dict_shape(tp) -> FullShape:
    # __annotations__ of TypedDict contain also parents' type hints unlike any other classes,
    # so overriden_types always is empty
    if not is_typed_dict_class(tp):
        raise IntrospectionImpossible

    type_hints = _get_td_hints(tp)

    if HAS_TYPED_DICT_REQUIRED:
        norm_types = [normalize_type(tp) for _, tp in type_hints]

        required_keys = _fetch_required_keys(
            [(field_name, field_tp) for (field_name, _), field_tp in zip(type_hints, norm_types)],
            tp.__required_keys__,
        )
        requirement_determinant = _make_requirement_determinant_from_keys(required_keys)
    else:
        requirement_determinant = _make_requirement_determinant_from_type(tp)

    return Shape(
        input=InputShape(
            constructor=tp,
            fields=tuple(
                InputField(
                    type=tp,
                    id=name,
                    default=NoDefault(),
                    is_required=requirement_determinant(name),
                    metadata=MappingProxyType({}),
                    original=None,
                )
                for name, tp in type_hints
            ),
            params=tuple(
                Param(
                    field_id=name,
                    name=name,
                    kind=ParamKind.KW_ONLY,
                )
                for name, tp in type_hints
            ),
            kwargs=None,
            overriden_types=frozenset({}),
        ),
        output=OutputShape(
            fields=tuple(
                OutputField(
                    type=tp,
                    id=name,
                    default=NoDefault(),
                    accessor=create_key_accessor(
                        key=name,
                        access_error=None if requirement_determinant(name) else KeyError,
                    ),
                    metadata=MappingProxyType({}),
                    original=None,
                )
                for name, tp in type_hints
            ),
            overriden_types=frozenset({}),
        ),
    )
