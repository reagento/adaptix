import warnings
from types import MappingProxyType

from ...feature_requirement import HAS_PY_39
from ...type_tools import get_all_type_hints, is_typed_dict_class
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
    def _td_make_requirement_determinant(tp):
        required_fields = tp.__required_keys__
        return lambda name: name in required_fields
else:
    def _td_make_requirement_determinant(tp):
        warnings.warn(TypedDictAt38Warning(), stacklevel=3)
        is_total = tp.__total__
        return lambda name: is_total


def get_typed_dict_shape(tp) -> FullShape:
    # __annotations__ of TypedDict contain also parents' type hints unlike any other classes,
    # so overriden_types always is empty
    if not is_typed_dict_class(tp):
        raise IntrospectionImpossible

    requirement_determinant = _td_make_requirement_determinant(tp)
    type_hints = _get_td_hints(tp)
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
