import inspect
from abc import abstractmethod, ABC
from dataclasses import is_dataclass, MISSING as DC_MISSING, Field as DCField, replace, fields as dc_fields
from inspect import Signature, Parameter
from types import MappingProxyType
from typing import Any, get_type_hints, final, Dict, Iterable, Callable

from .definitions import (
    InputFigure, OutputFigure,
    InputFigureRequest, OutputFigureRequest,
    ExtraKwargs,
)
from ..definitions import DefaultValue, DefaultFactory, Default, NoDefault, AttrAccessor, ItemAccessor
from ..essential import Mediator, CannotProvide
from ..request_cls import InputFieldRM, ParamKind, OutputFieldRM
from ..static_provider import StaticProvider, static_provision_action
from ...type_tools import is_typed_dict_class, is_named_tuple_class

_PARAM_KIND_CONV: Dict[Any, ParamKind] = {
    Parameter.POSITIONAL_ONLY: ParamKind.POS_ONLY,
    Parameter.POSITIONAL_OR_KEYWORD: ParamKind.POS_OR_KW,
    Parameter.KEYWORD_ONLY: ParamKind.KW_ONLY,
}


def get_func_inp_fig(func, params_slice=slice(0, None)) -> InputFigure:
    params = list(
        inspect.signature(func).parameters.values()
    )[params_slice]

    return signature_params_to_inp_fig(func, params)


def _is_empty(value):
    return value is Signature.empty


def signature_params_to_inp_fig(constructor: Callable, params: Iterable[Parameter]) -> InputFigure:
    kinds = [p.kind for p in params]

    if Parameter.VAR_POSITIONAL in kinds:
        raise ValueError(
            f'Can not create InputFigure'
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


class TypeOnlyInputFigureProvider(StaticProvider, ABC):
    # noinspection PyUnusedLocal
    @final
    @static_provision_action(InputFigureRequest)
    def _provide_input_figure(self, mediator: Mediator, request: InputFigureRequest) -> InputFigure:
        return self._get_input_figure(request.type)

    @abstractmethod
    def _get_input_figure(self, tp) -> InputFigure:
        pass


class TypeOnlyOutputFigureProvider(StaticProvider, ABC):
    # noinspection PyUnusedLocal
    @final
    @static_provision_action(OutputFigureRequest)
    def _provide_output_figure(self, mediator: Mediator, request: InputFigureRequest) -> OutputFigure:
        return self._get_output_figure(request.type)

    @abstractmethod
    def _get_output_figure(self, tp) -> OutputFigure:
        pass


class NamedTupleFigureProvider(TypeOnlyInputFigureProvider, TypeOnlyOutputFigureProvider):
    def _get_input_figure(self, tp) -> InputFigure:
        if not is_named_tuple_class(tp):
            raise CannotProvide

        iff = get_func_inp_fig(tp.__new__, slice(1, None))

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

    def _get_output_figure(self, tp) -> OutputFigure:
        return OutputFigure(
            fields=tuple(
                OutputFieldRM(
                    name=fld.name,
                    type=fld.type,
                    default=fld.default,
                    metadata=fld.metadata,
                    accessor=AttrAccessor(attr_name=fld.name, is_required=True),
                )
                for fld in self._get_input_figure(tp).fields
            ),
            extra=None,
        )


class TypedDictFigureProvider(TypeOnlyInputFigureProvider, TypeOnlyOutputFigureProvider):
    def _get_fields_are_required(self, tp) -> bool:
        if not is_typed_dict_class(tp):
            raise CannotProvide

        return tp.__total__

    def _get_input_figure(self, tp):
        are_required = self._get_fields_are_required(tp)

        return InputFigure(
            constructor=tp,
            fields=tuple(
                InputFieldRM(
                    type=tp,
                    name=name,
                    default=NoDefault(),
                    is_required=are_required,
                    metadata=MappingProxyType({}),
                    param_kind=ParamKind.KW_ONLY,
                )
                for name, tp in get_type_hints(tp).items()
            ),
            extra=None,
        )

    def _get_output_figure(self, tp):
        are_required = self._get_fields_are_required(tp)

        return OutputFigure(
            fields=tuple(
                OutputFieldRM(
                    type=tp,
                    name=name,
                    default=NoDefault(),
                    accessor=ItemAccessor(name, are_required),
                    metadata=MappingProxyType({}),
                )
                for name, tp in get_type_hints(tp).items()
            ),
            extra=None,
        )


def all_dc_fields(cls) -> Dict[str, DCField]:
    """Builtin introspection function hides
    some fields like InitVar or ClassVar.
    That function return full dict
    """
    return cls.__dataclass_fields__


def get_dc_default(field: DCField) -> Default:
    if field.default is not DC_MISSING:
        return DefaultValue(field.default)
    if field.default_factory is not DC_MISSING:
        return DefaultFactory(field.default_factory)
    return NoDefault()


def create_inp_field_rm(dc_field: DCField):
    default = get_dc_default(dc_field)
    return InputFieldRM(
        type=dc_field.type,
        name=dc_field.name,
        default=default,
        is_required=default == NoDefault(),
        metadata=dc_field.metadata,
        param_kind=ParamKind.POS_OR_KW,
    )


class DataclassFigureProvider(TypeOnlyInputFigureProvider, TypeOnlyOutputFigureProvider):
    """This provider does not work properly if __init__ signature differs from
    that would be created by dataclass decorator.

    It happens because we can not distinguish __init__ that generated
    by @dataclass and __init__ that created by other ways.
    And we can not analyze only __init__ signature
    because @dataclass uses private constant
    as default value for fields with default_factory
    """

    def _get_input_figure(self, tp):
        if not is_dataclass(tp):
            raise CannotProvide

        name_to_dc_field = all_dc_fields(tp)

        init_params = list(
            inspect.signature(tp.__init__).parameters.keys()
        )[1:]

        return InputFigure(
            constructor=tp,
            fields=tuple(
                create_inp_field_rm(name_to_dc_field[field_name])
                for field_name in init_params
            ),
            extra=None,
        )

    def _get_output_figure(self, tp):
        if not is_dataclass(tp):
            raise CannotProvide

        name_to_dc_field = all_dc_fields(tp)

        return OutputFigure(
            fields=tuple(
                OutputFieldRM(
                    type=field.type,
                    name=field.name,
                    default=get_dc_default(name_to_dc_field[field.name]),
                    accessor=AttrAccessor(field.name, True),
                    metadata=field.metadata,
                )
                for field in dc_fields(tp)
            ),
            extra=None,
        )


class ClassInitInputFigureProvider(TypeOnlyInputFigureProvider):
    def _get_input_figure(self, tp):
        if not isinstance(tp, type):
            raise CannotProvide

        try:
            iff = get_func_inp_fig(
                tp.__init__, slice(1, None)
            )
        except ValueError:
            raise CannotProvide

        return replace(
            iff,
            constructor=tp,
        )
