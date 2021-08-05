import inspect
from abc import abstractmethod
from dataclasses import dataclass, fields as dc_fields, is_dataclass, MISSING as DC_MISSING, Field as DCField
from inspect import Signature, Parameter
from types import MappingProxyType
from typing import Any, Callable, Union, List, get_type_hints

from ..core import ProvisionCtx, Provider, BaseFactory, provision_action, CannotProvide
from ..type_tools import is_subclass_soft
from ..type_tools.utils import is_typed_dict_class, is_named_tuple_class


@dataclass(frozen=True)
class NoDefault:
    field_is_required: bool


@dataclass(frozen=True)
class DefaultValue:
    value: Any


@dataclass(frozen=True)
class DefaultFactory:
    factory: Callable[[], Any]


Default = Union[NoDefault, DefaultValue, DefaultFactory]


@dataclass(frozen=True)
class FieldsProvisionCtx(ProvisionCtx):
    field_name: str
    default: Default
    metadata: MappingProxyType


class InputFieldsProvider(Provider[List[FieldsProvisionCtx]]):
    @abstractmethod
    @provision_action
    def _provide_input_fields(
        self,
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> List[FieldsProvisionCtx]:
        pass


class OutputFieldsProvider(Provider[List[FieldsProvisionCtx]]):
    @abstractmethod
    @provision_action
    def _provide_output_fields(
        self,
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> List[FieldsProvisionCtx]:
        pass


def get_func_fields_prov_ctx(func, slice_=slice(0, None)) -> List[FieldsProvisionCtx]:
    params = list(
        inspect.signature(func).parameters.values()
    )[slice_]

    if not all(
        p.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY)
        for p in params
    ):
        raise ValueError(
            'Can not create consistent FieldsProvisionCtx'
            ' from the function that has not only'
            ' POSITIONAL_OR_KEYWORD or KEYWORD_ONLY parameters'
        )

    return [
        FieldsProvisionCtx(
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
    ]


NAMED_TUPLE_METHODS = {'_fields', '_field_defaults', '_make', '_replace', '_asdict'}


class NamedTupleFieldsProvider(InputFieldsProvider, OutputFieldsProvider):
    def _get_fields(self, tp: type) -> List[FieldsProvisionCtx]:
        if not is_named_tuple_class(tp):
            raise CannotProvide

        return get_func_fields_prov_ctx(tp.__new__, slice(1, None))

    def _provide_input_fields(
        self,
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> List[FieldsProvisionCtx]:
        return self._get_fields(ctx.type)

    def _provide_output_fields(
        self,
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> List[FieldsProvisionCtx]:
        return self._get_fields(ctx.type)


class TypedDictInputFieldsProvider(InputFieldsProvider):
    def _get_fields(self, tp):
        if not is_typed_dict_class(tp):
            raise CannotProvide

        is_required = tp.__total__

        return [
            FieldsProvisionCtx(
                type=tp,
                field_name=name,
                default=NoDefault(field_is_required=is_required),
                metadata=MappingProxyType({}),
            )
            for name, tp in get_type_hints(tp).items()
        ]

    def _provide_input_fields(
        self,
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> List[FieldsProvisionCtx]:
        return self._get_fields(ctx.type)


def get_dc_default(field: DCField) -> Default:
    if field.default is not DC_MISSING:
        return DefaultValue(field.default)
    if field.default_factory is not DC_MISSING:
        return DefaultFactory(field.default_factory)
    return NoDefault(field_is_required=True)


class DataclassFieldsProvider(InputFieldsProvider, OutputFieldsProvider):
    def _get_fields_filtered(self, tp, filer_func):
        if not is_dataclass(tp):
            raise CannotProvide

        return [
            FieldsProvisionCtx(
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

    def _provide_input_fields(
        self,
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> List[FieldsProvisionCtx]:
        return self._get_input_fields(ctx.type)

    def _get_output_fields(self, tp):
        return self._get_fields_filtered(
            tp, lambda fld: True
        )

    def _provide_output_fields(
        self,
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> List[FieldsProvisionCtx]:
        return self._get_output_fields(ctx.type)


class ClassInitFieldsProvider(InputFieldsProvider):
    def _get_fields(self, tp):
        if not isinstance(tp, type):
            raise CannotProvide

        try:
            return get_func_fields_prov_ctx(
                tp.__init__, slice(1, None)
            )
        except ValueError:
            raise CannotProvide

    def _provide_input_fields(
        self,
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> List[FieldsProvisionCtx]:
        return self._get_fields(ctx.type)
