import warnings
from types import MappingProxyType
from typing import Sequence, Tuple

from ...feature_requirement import HAS_PY_39, HAS_PY_311
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


if HAS_PY_39:
    def _make_requirement_determinant(tp):
        required_fields = tp.__required_keys__
        return lambda name: name in required_fields
else:
    def _make_requirement_determinant(tp):
        warnings.warn(TypedDictAt38Warning(), stacklevel=3)
        is_total = tp.__total__
        return lambda name: is_total


if HAS_PY_311:
    from typing import NotRequired, Required

    def _correct_required_and_optional_keys(
        fields: Sequence[Tuple[str, BaseNormType]],
        frozen_required_keys: frozenset[str],
        frozen_optional_keys: frozenset[str],
    ) -> Tuple[frozenset, frozenset]:
        required_keys = set(frozen_required_keys)
        optional_keys = set(frozen_optional_keys)

        for field_name, field_tp in fields:
            if field_tp.origin is Required and field_name in optional_keys:
                optional_keys.remove(field_name)
                required_keys.add(field_name)
            elif field_tp.origin is NotRequired and field_name in required_keys:
                required_keys.remove(field_name)
                optional_keys.add(field_name)

        return frozenset(required_keys), frozenset(optional_keys)


def get_typed_dict_shape(tp) -> FullShape:
    # __annotations__ of TypedDict contain also parents' type hints unlike any other classes,
    # so overriden_types always is empty
    if not is_typed_dict_class(tp):
        raise IntrospectionImpossible

    type_hints = _get_td_hints(tp)

    if HAS_PY_311:
        norm_types = [normalize_type(tp) for _, tp in type_hints]

        fields_keys = _correct_required_and_optional_keys(
            [(field_name, field_tp) for (field_name, _), field_tp in zip(type_hints, norm_types)],
            tp.__required_keys__,
            tp.__optional_keys__,
        )
        tp.__required_keys__ = fields_keys[0]
        tp.__optional_keys__ = fields_keys[1]

    requirement_determinant = _make_requirement_determinant(tp)

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
