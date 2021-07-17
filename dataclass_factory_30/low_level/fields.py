import inspect
from abc import abstractmethod
from dataclasses import dataclass
from inspect import Signature
from types import MappingProxyType
from typing import Any, Callable, Union, List, get_type_hints

from ..core import ProvisionCtx, Provider, BaseFactory, provision_action, CannotProvide
from ..type_tools import is_subclass_soft
from ..type_tools.utils import is_typed_dict


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


class DataclassFieldsProvider(InputFieldsProvider, OutputFieldsProvider):
    def _provide_input_fields(
        self,
        factory: 'BaseFactory',
        offset: int,
        ctx: ProvisionCtx
    ) -> List[FieldsProvisionCtx]:
        pass

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
        if not (
            is_subclass_soft(tp, tuple)
            and
            NAMED_TUPLE_METHODS.issubset(vars(tp))
        ):
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
        if not is_typed_dict(tp):
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
