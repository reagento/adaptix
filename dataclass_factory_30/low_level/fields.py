import inspect
from dataclasses import dataclass, fields as dc_fields, is_dataclass, MISSING as DC_MISSING, Field as DCField
from enum import Enum
from inspect import Signature, Parameter
from operator import getitem
from types import MappingProxyType
from typing import Any, List, get_type_hints, Union, Generic, TypeVar, Optional, Callable

from .request_cls import TypeFieldRequest, NoDefault, DefaultValue, Default, DefaultFactory
from ..core import BaseFactory, CannotProvide, Provider, provision_action, SearchState, Request
from ..type_tools.utils import is_typed_dict_class, is_named_tuple_class

T = TypeVar('T')


class GetterKind(Enum):
    ATTR = 0
    ITEM = 1

    def to_function(self) -> Callable[[Any, str], Any]:
        return _GETTER_KIND_TO_FUNCTION[self]  # type: ignore


_GETTER_KIND_TO_FUNCTION = {
    GetterKind.ATTR: getattr,
    GetterKind.ITEM: getitem,
}


class ExtraVariant(Enum):
    SKIP = 0
    FORBID = 1
    KWARGS = 2


@dataclass(frozen=True)
class ExtraTargets:
    fields: List[str]


Extra = Union[ExtraVariant, ExtraTargets]


@dataclass
class InputFieldsFigure:
    fields: List[TypeFieldRequest]
    extra: Optional[Extra]


@dataclass
class OutputFieldsFigure:
    fields: List[TypeFieldRequest]
    getter_kind: GetterKind


class BaseFFRequest(Request, Generic[T]):
    type: type


class InputFFRequest(BaseFFRequest[InputFieldsFigure]):
    pass


class OutputFFRequest(BaseFFRequest[OutputFieldsFigure]):
    pass


def get_func_iff(func, slice_=slice(0, None)) -> InputFieldsFigure:
    params = list(
        inspect.signature(func).parameters.values()
    )[slice_]

    if not all(
        p.kind in (
            Parameter.POSITIONAL_OR_KEYWORD,
            Parameter.KEYWORD_ONLY,
            Parameter.VAR_KEYWORD
        )
        for p in params
    ):
        raise ValueError(
            'Can not create consistent InputFieldsFigure'
            ' from the function that has not only'
            ' POSITIONAL_OR_KEYWORD or KEYWORD_ONLY or VAR_KEYWORD'
            ' parameters'
        )

    extra: Optional[Extra]
    if any(p.kind == Parameter.VAR_KEYWORD for p in params):
        extra = ExtraVariant.KWARGS
    else:
        extra = None

    return InputFieldsFigure(
        fields=[
            TypeFieldRequest(
                type=(
                    Any
                    if param.annotation is Signature.empty
                    else param.annotation
                ),
                field_name=param.name,
                default=(
                    NoDefault(field_is_required=True)
                    if param.default is Signature.empty
                    else DefaultValue(param.default)
                ),
                metadata=MappingProxyType({}),
            )
            for param in params
        ],
        extra=extra,
    )


class NamedTupleFieldsProvider(Provider):
    def _get_input_fields_figure(self, tp: type) -> InputFieldsFigure:
        if not is_named_tuple_class(tp):
            raise CannotProvide

        return get_func_iff(tp.__new__, slice(1, None))

    # noinspection PyUnusedLocal
    @provision_action(InputFFRequest)
    def _provide_input_fields_figure(
        self,
        factory: BaseFactory,
        s_state: SearchState,
        request: InputFFRequest
    ) -> InputFieldsFigure:
        return self._get_input_fields_figure(request.type)

    # noinspection PyUnusedLocal
    @provision_action(OutputFFRequest)
    def _provide_output_fields_figure(
        self,
        factory: BaseFactory,
        s_state: SearchState,
        request: OutputFFRequest
    ) -> OutputFieldsFigure:
        return OutputFieldsFigure(
            fields=self._get_input_fields_figure(request.type).fields,
            getter_kind=GetterKind.ATTR,
        )


class TypedDictFieldsProvider(Provider):
    def _get_fields(self, tp):
        if not is_typed_dict_class(tp):
            raise CannotProvide

        is_required = tp.__total__

        return [
            TypeFieldRequest(
                type=tp,
                field_name=name,
                default=NoDefault(field_is_required=is_required),
                metadata=MappingProxyType({}),
            )
            for name, tp in get_type_hints(tp).items()
        ]

    # noinspection PyUnusedLocal
    @provision_action(InputFFRequest)
    def _provide_input_fields_figure(
        self,
        factory: BaseFactory,
        s_state: SearchState,
        request: InputFFRequest
    ) -> InputFieldsFigure:
        return InputFieldsFigure(
            fields=self._get_fields(request.type),  # type: ignore
            extra=None,
        )

    # noinspection PyUnusedLocal
    @provision_action(OutputFFRequest)
    def _provide_output_fields_figure(
        self,
        factory: BaseFactory,
        s_state: SearchState,
        request: OutputFFRequest
    ) -> OutputFieldsFigure:
        return OutputFieldsFigure(
            fields=self._get_fields(request.type),  # type: ignore
            getter_kind=GetterKind.ITEM,
        )


def get_dc_default(field: DCField) -> Default:
    if field.default is not DC_MISSING:
        return DefaultValue(field.default)
    if field.default_factory is not DC_MISSING:
        return DefaultFactory(field.default_factory)
    return NoDefault(field_is_required=True)


class DataclassFieldsProvider(Provider):
    """This provider does not work properly if __init__ signature differs from
    that would be created by dataclass decorator.

    It happens because we can not distinguish __init__ that generated
    by @dataclass and __init__ that created by other ways.
    And we can not analyze only __init__ signature
    because @dataclass uses private constant
    as default value for fields with default_factory
    """

    def _get_fields_filtered(self, tp, filer_func):
        if not is_dataclass(tp):
            raise CannotProvide

        return [
            TypeFieldRequest(
                type=fld.type,
                field_name=fld.name,
                default=get_dc_default(fld),
                metadata=MappingProxyType(fld.metadata),
            )
            for fld in dc_fields(tp)
            if filer_func(fld)
        ]

    def _get_input_fields(self, tp):
        return self._get_fields_filtered(
            tp, lambda fld: fld.init
        )

    # noinspection PyUnusedLocal
    @provision_action(InputFFRequest)
    def _provide_input_fields_figure(
        self,
        factory: BaseFactory,
        s_state: SearchState,
        request: InputFFRequest
    ) -> InputFieldsFigure:
        return InputFieldsFigure(
            fields=self._get_input_fields(request.type),
            extra=None,
        )

    def _get_output_fields(self, tp):
        return self._get_fields_filtered(
            tp, lambda fld: True
        )

    # noinspection PyUnusedLocal
    @provision_action(OutputFFRequest)
    def _provide_output_fields_figure(
        self,
        factory: BaseFactory,
        s_state: SearchState,
        request: OutputFFRequest
    ) -> OutputFieldsFigure:
        return OutputFieldsFigure(
            fields=self._get_output_fields(request.type),
            getter_kind=GetterKind.ATTR,
        )


class ClassInitFieldsProvider(Provider):
    def _get_input_fields_figure(self, tp):
        if not isinstance(tp, type):
            raise CannotProvide

        try:
            return get_func_iff(
                tp.__init__, slice(1, None)
            )
        except ValueError:
            raise CannotProvide

    # noinspection PyUnusedLocal
    @provision_action(InputFFRequest)
    def _provide_input_fields_figure(
        self,
        factory: BaseFactory,
        s_state: SearchState,
        request: InputFFRequest
    ) -> InputFieldsFigure:
        return self._get_input_fields_figure(request.type)
