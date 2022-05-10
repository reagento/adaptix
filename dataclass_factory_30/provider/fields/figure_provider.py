import inspect
from abc import abstractmethod, ABC
from dataclasses import fields as dc_fields, is_dataclass, MISSING as DC_MISSING, Field as DCField, replace
from inspect import Signature, Parameter
from types import MappingProxyType
from typing import Any, get_type_hints, final, Dict, Iterable, Callable, Tuple

from ..definitions import DefaultValue, DefaultFactory, Default, NoDefault
from ..essential import Mediator, CannotProvide
from .definitions import (
    InputFigure, OutputFigure,
    InputFFRequest, OutputFFRequest,
    ExtraKwargs
)
from ..request_cls import FieldRM, InputFieldRM, ParamKind, OutputFieldRM, AccessKind
from ..static_provider import StaticProvider, static_provision_action
from ...type_tools import is_typed_dict_class, is_named_tuple_class

_PARAM_KIND_CONV: Dict[Any, ParamKind] = {
    Parameter.POSITIONAL_ONLY: ParamKind.POS_ONLY,
    Parameter.POSITIONAL_OR_KEYWORD: ParamKind.POS_OR_KW,
    Parameter.KEYWORD_ONLY: ParamKind.KW_ONLY,
}


def get_func_iff(func, params_slice=slice(0, None)) -> InputFigure:
    params = list(
        inspect.signature(func).parameters.values()
    )[params_slice]

    return signature_params_to_iff(func, params)


def _is_empty(value):
    return value is Signature.empty


def signature_params_to_iff(constructor: Callable, params: Iterable[Parameter]) -> InputFigure:
    kinds = [p.kind for p in params]

    if Parameter.VAR_POSITIONAL in kinds:
        raise ValueError(
            f'Can not create InputFieldsFigure'
            f' from the function that has {Parameter.VAR_POSITIONAL}'
            f' parameter'
        )

    extra = (
        ExtraKwargs()
        if Parameter.VAR_KEYWORD in kinds else
        None
    )

    return InputFigure(
        constructor=constructor,
        fields=tuple(
            InputFieldRM(
                type=Any if _is_empty(param.annotation) else param.annotation,
                name=param.name,
                is_required=_is_empty(param.default),
                default=NoDefault() if _is_empty(param.default) else DefaultValue(param.default),
                metadata=MappingProxyType({}),
                param_kind=_PARAM_KIND_CONV[param.kind],
            )
            for param in params
            if param.kind != Parameter.VAR_KEYWORD
        ),
        extra=extra,
    )


class TypeOnlyInputFFProvider(StaticProvider, ABC):
    # noinspection PyUnusedLocal
    @final
    @static_provision_action(InputFFRequest)
    def _provide_input_fields_figure(self, mediator: Mediator, request: InputFFRequest) -> InputFigure:
        return self._get_input_fields_figure(request.type)

    @abstractmethod
    def _get_input_fields_figure(self, tp) -> InputFigure:
        pass


class TypeOnlyOutputFFProvider(StaticProvider, ABC):
    # noinspection PyUnusedLocal
    @final
    @static_provision_action(OutputFFRequest)
    def _provide_output_fields_figure(self, mediator: Mediator, request: OutputFFRequest) -> OutputFigure:
        return self._get_output_fields_figure(request.type)

    @abstractmethod
    def _get_output_fields_figure(self, tp) -> OutputFigure:
        pass


class NamedTupleFieldsProvider(TypeOnlyInputFFProvider, TypeOnlyOutputFFProvider):
    def _get_input_fields_figure(self, tp) -> InputFigure:
        if not is_named_tuple_class(tp):
            raise CannotProvide

        iff = get_func_iff(tp.__new__, slice(1, None))

        type_hints = get_type_hints(tp)

        # At <3.9 namedtuple does not generate typehints at __new__
        return InputFigure(
            constructor=tp,
            extra=iff.extra,  # maybe for custom __init__?
            fields=tuple(
                replace(
                    fld,
                    type=type_hints.get(fld.name, Any)
                )
                for fld in iff.fields
            )
        )

    def _get_output_fields_figure(self, tp) -> OutputFigure:
        return OutputFigure(
            fields=tuple(
                OutputFieldRM(
                    name=fld.name,
                    type=fld.type,
                    default=fld.default,
                    is_required=True,
                    metadata=fld.metadata,
                    access_kind=AccessKind.ATTR,
                )
                for fld in self._get_input_fields_figure(tp).fields
            ),
            extra=None,
        )


def _to_inp(param_kind: ParamKind, fields: Iterable[FieldRM]) -> Tuple[InputFieldRM, ...]:
    return tuple(
        InputFieldRM(
            name=f.name,
            type=f.type,
            default=f.default,
            is_required=f.is_required,
            metadata=f.metadata,
            param_kind=param_kind,
        )
        for f in fields
    )


def _to_out(access_kind: AccessKind, fields: Iterable[FieldRM]) -> Tuple[OutputFieldRM, ...]:
    return tuple(
        OutputFieldRM(
            name=f.name,
            type=f.type,
            default=f.default,
            is_required=f.is_required,
            metadata=f.metadata,
            access_kind=access_kind,
        )
        for f in fields
    )


class TypedDictFieldsProvider(TypeOnlyInputFFProvider, TypeOnlyOutputFFProvider):
    def _get_fields(self, tp):
        if not is_typed_dict_class(tp):
            raise CannotProvide

        is_required = tp.__total__

        return tuple(
            FieldRM(
                type=tp,
                name=name,
                default=NoDefault(),
                is_required=is_required,
                metadata=MappingProxyType({}),
            )
            for name, tp in get_type_hints(tp).items()
        )

    def _get_input_fields_figure(self, tp):
        return InputFigure(
            constructor=tp,
            fields=_to_inp(ParamKind.KW_ONLY, self._get_fields(tp)),
            extra=None,
        )

    def _get_output_fields_figure(self, tp):
        return OutputFigure(
            fields=_to_out(AccessKind.ITEM, self._get_fields(tp)),
            extra=None,
        )


def get_dc_default(field: DCField) -> Default:
    if field.default is not DC_MISSING:
        return DefaultValue(field.default)
    if field.default_factory is not DC_MISSING:
        return DefaultFactory(field.default_factory)
    return NoDefault()


def _dc_field_to_field_rm(fld: DCField, required_det: Callable[[Default], bool]):
    default = get_dc_default(fld)

    return FieldRM(
        type=fld.type,
        name=fld.name,
        default=default,
        is_required=required_det(default),
        metadata=fld.metadata,
    )


def all_dc_fields(cls) -> Dict[str, DCField]:
    """Builtin introspection function hides
    some fields like InitVar or ClassVar.
    That function return full dict
    """
    return cls.__dataclass_fields__


class DataclassFieldsProvider(TypeOnlyInputFFProvider, TypeOnlyOutputFFProvider):
    """This provider does not work properly if __init__ signature differs from
    that would be created by dataclass decorator.

    It happens because we can not distinguish __init__ that generated
    by @dataclass and __init__ that created by other ways.
    And we can not analyze only __init__ signature
    because @dataclass uses private constant
    as default value for fields with default_factory
    """

    def _get_input_fields_figure(self, tp):
        if not is_dataclass(tp):
            raise CannotProvide

        name_to_dc_field = all_dc_fields(tp)

        init_params = list(
            inspect.signature(tp.__init__).parameters.keys()
        )[1:]

        return InputFigure(
            constructor=tp,
            fields=_to_inp(
                ParamKind.POS_OR_KW,
                [
                    _dc_field_to_field_rm(
                        name_to_dc_field[field_name],
                        lambda default: default == NoDefault()
                    )
                    for field_name in init_params
                ]
            ),
            extra=None,
        )

    def _get_output_fields_figure(self, tp):
        if not is_dataclass(tp):
            raise CannotProvide

        return OutputFigure(
            fields=_to_out(
                AccessKind.ATTR,
                [
                    _dc_field_to_field_rm(fld, lambda default: True)
                    for fld in dc_fields(tp)
                ]
            ),
            extra=None,
        )


class ClassInitFieldsProvider(TypeOnlyInputFFProvider):
    def _get_input_fields_figure(self, tp):
        if not isinstance(tp, type):
            raise CannotProvide

        try:
            iff = get_func_iff(
                tp.__init__, slice(1, None)
            )
        except ValueError:
            raise CannotProvide

        return replace(
            iff,
            constructor=tp,
        )
