import inspect
import itertools
from inspect import Parameter, Signature
from typing import Any, Callable, Optional, Protocol, Sequence, Type

from pydantic import AliasChoices, BaseModel
from pydantic.fields import ComputedFieldInfo, FieldInfo
from pydantic_core import PydanticUndefined

from adaptix import TypeHint

from ...feature_requirement import HAS_PYDANTIC_PKG, HAS_SUPPORTED_PYDANTIC_PKG
from ...type_tools import get_all_type_hints, is_subclass_soft
from ..definitions import (
    ClarifiedIntrospectionError,
    Default,
    DefaultFactory,
    DefaultValue,
    FullShape,
    InputField,
    InputShape,
    IntrospectionError,
    NoDefault,
    NoTargetPackageError,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    ParamKwargs,
    Shape,
    TooOldPackageError,
    create_attr_accessor,
)


class WithDefaults(Protocol):
    default: Any
    default_factory: Optional[Callable[[], Any]]


def _get_default(field: WithDefaults) -> Default:
    if field.default_factory is not None:
        return DefaultFactory(field.default_factory)
    if field.default is PydanticUndefined:
        return NoDefault()
    return DefaultValue(field.default)


def _get_field_parameters(tp: "Type[BaseModel]", field_name: str, field_info: "FieldInfo") -> Sequence[str]:
    # AliasPath is ignored
    parameters = [field_name] if tp.model_config["populate_by_name"] else []

    if field_info.validation_alias is None:
        parameters.append(field_name)
    elif isinstance(field_info.validation_alias, str):
        parameters.append(field_info.validation_alias)
    elif isinstance(field_info.validation_alias, AliasChoices):
        parameters.extend(alias for alias in field_info.validation_alias.choices if isinstance(alias, str))
    return parameters


def _signature_is_kwargs_only(init_signature: Signature) -> bool:
    if len(init_signature.parameters) > 1:
        return False
    param = next(iter(init_signature.parameters.values()))
    return param.kind != Parameter.VAR_KEYWORD


def _get_input_shape(tp: "Type[BaseModel]") -> InputShape:
    if not _signature_is_kwargs_only(inspect.signature(tp.__init__)):
        raise ClarifiedIntrospectionError(
            "Pydantic model `__init__` must have only one variable keyword parameter",
        )

    return InputShape(
        constructor=tp,
        fields=tuple(
            InputField(
                id=field_id,
                type=field_info.annotation,
                default=_get_default(field_info),
                metadata={},  # pydantic metadata is the list
                original=field_info,
                is_required=_get_default(field_info) == NoDefault(),
            )
            for field_id, field_info in tp.model_fields.items()
        ),
        overriden_types=frozenset(
            field_id for field_id in tp.model_fields
            if field_id in tp.__annotations__
        ),
        params=tuple(
            Param(
                field_id=field_id,
                kind=ParamKind.KW_ONLY,
                name=_get_field_parameters(tp, field_id, field_info)[0],
            )
            for field_id, field_info in tp.model_fields.items()
        ),
        kwargs=None if tp.model_config["extra"] == "forbid" else ParamKwargs(Any),
    )


def _get_computed_field_type(field_id: str, computed_field_info: "ComputedFieldInfo") -> TypeHint:
    # computed_field_info.return_type is always equals PydanticUndefined
    prop = computed_field_info.wrapped_property
    if prop.fget is None:
        raise ClarifiedIntrospectionError(f"Computed field {field_id!r} has no getter")

    signature = inspect.signature(prop.fget)
    if signature.return_annotation is inspect.Signature.empty:
        return Any
    return signature.return_annotation


def _get_output_shape(tp: "Type[BaseModel]") -> OutputShape:
    type_hints = get_all_type_hints(tp)
    fields = itertools.chain(
        (
            OutputField(
                id=field_id,
                type=field_info.annotation,
                default=_get_default(field_info),
                metadata={},  # pydantic metadata is the list
                original=field_info,
                accessor=create_attr_accessor(field_id, is_required=True),
            )
            for field_id, field_info in tp.model_fields.items()
        ),
        (
            OutputField(
                id=field_id,
                type=_get_computed_field_type(field_id, computed_field_dec.info),
                default=NoDefault(),
                metadata={},
                original=computed_field_dec,
                accessor=create_attr_accessor(field_id, is_required=True),
            )
            for field_id, computed_field_dec in tp.__pydantic_decorators__.computed_fields.items()
        ),
        (
            OutputField(
                id=field_id,
                type=type_hints[field_id],
                default=_get_default(private_attr),
                metadata={},
                original=private_attr,
                accessor=create_attr_accessor(field_id, is_required=True),
            )
            for field_id, private_attr in tp.__private_attributes__.items()
        ),
    )
    return OutputShape(
        fields=tuple(fields),
        overriden_types=frozenset(
            itertools.chain(
                (
                    field_id for field_id in itertools.chain(tp.model_fields, tp.__private_attributes__)
                    if field_id in tp.__annotations__
                ),
                (
                    field_id for field_id in tp.__pydantic_decorators__.computed_fields
                    if field_id in tp.__dict__
                ),
            ),
        ),
    )


def get_pydantic_shape(tp) -> FullShape:
    if not HAS_SUPPORTED_PYDANTIC_PKG:
        if not HAS_PYDANTIC_PKG:
            raise NoTargetPackageError(HAS_PYDANTIC_PKG)
        raise TooOldPackageError(HAS_SUPPORTED_PYDANTIC_PKG)

    if not is_subclass_soft(tp, BaseModel):
        raise IntrospectionError

    return Shape(
        input=_get_input_shape(tp),
        output=_get_output_shape(tp),
    )
