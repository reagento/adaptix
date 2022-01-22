import inspect
from abc import abstractmethod, ABC
from dataclasses import dataclass, fields as dc_fields, is_dataclass, MISSING as DC_MISSING, Field as DCField
from enum import Enum
from inspect import Signature, Parameter
from itertools import islice
from types import MappingProxyType
from typing import Any, List, get_type_hints, Union, Generic, TypeVar, final, Dict, Iterable

from .definitions import DefaultValue, DefaultFactory, Default, NoDefault
from .essential import Mediator, CannotProvide, Request
from .request_cls import FieldRM, TypeHintRM, InputFieldRM, ParamKind
from .static_provider import StaticProvider, static_provision_action
from ..singleton import SingletonMeta
from ..type_tools import is_typed_dict_class, is_named_tuple_class

T = TypeVar('T')


class GetterKind(Enum):
    ATTR = 0
    ITEM = 1


class ExtraSkip(metaclass=SingletonMeta):
    pass


class ExtraForbid(metaclass=SingletonMeta):
    pass


class ExtraKwargs(metaclass=SingletonMeta):
    pass


@dataclass(frozen=True)
class ExtraTargets:
    fields: List[str]


class ExtraCollect(metaclass=SingletonMeta):
    pass


FigureExtra = Union[None, ExtraKwargs, ExtraTargets]

ExtraPolicy = Union[ExtraSkip, ExtraForbid, ExtraCollect]


class CfgExtraPolicy(Request[ExtraPolicy]):
    pass


@dataclass
class InputFieldsFigure:
    fields: List[InputFieldRM]
    extra: FigureExtra

    def __post_init__(self):
        for past, current in zip(self.fields, islice(self.fields, 1)):
            if past.param_kind.value > current.param_kind.value:
                raise ValueError(
                    f"Inconsistent order of fields,"
                    f" {current.param_kind} must be after {past.param_kind}"
                )

            if (
                not past.is_required
                and current.is_required
                and current.param_kind != ParamKind.KW_ONLY
            ):
                raise ValueError(
                    f"All not required fields must be after required ones"
                    f" except {ParamKind.KW_ONLY} fields"
                )


@dataclass
class OutputFieldsFigure:
    fields: List[FieldRM]
    getter_kind: GetterKind


class BaseFFRequest(TypeHintRM[T], Generic[T]):
    pass


class InputFFRequest(BaseFFRequest[InputFieldsFigure]):
    pass


class OutputFFRequest(BaseFFRequest[OutputFieldsFigure]):
    pass


_PARAM_KIND_CONV: Dict[Any, ParamKind] = {
    Parameter.POSITIONAL_ONLY: ParamKind.POS_ONLY,
    Parameter.POSITIONAL_OR_KEYWORD: ParamKind.POS_OR_KW,
    Parameter.KEYWORD_ONLY: ParamKind.KW_ONLY,
}


def get_func_iff(func, params_slice=slice(0, None)) -> InputFieldsFigure:
    params = list(
        inspect.signature(func).parameters.values()
    )[params_slice]

    return signature_params_to_iff(params)


def _is_empty(value):
    return value is Signature.empty


def signature_params_to_iff(params: Iterable[Parameter]) -> InputFieldsFigure:
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

    return InputFieldsFigure(
        fields=[
            InputFieldRM(
                type=Any if _is_empty(param.annotation) else param.annotation,
                field_name=param.name,
                is_required=_is_empty(param.default),
                default=NoDefault() if _is_empty(param.default) else DefaultValue(param.default),
                metadata=MappingProxyType({}),
                param_kind=_PARAM_KIND_CONV[param.kind],
            )
            for param in params
            if param.kind != Parameter.VAR_KEYWORD
        ],
        extra=extra,
    )


class TypeOnlyInputFFProvider(StaticProvider, ABC):
    # noinspection PyUnusedLocal
    @final
    @static_provision_action(InputFFRequest)
    def _provide_input_fields_figure(self, mediator: Mediator, request: InputFFRequest) -> InputFieldsFigure:
        return self._get_input_fields_figure(request.type)

    @abstractmethod
    def _get_input_fields_figure(self, tp) -> InputFieldsFigure:
        pass


class TypeOnlyOutputFFProvider(StaticProvider, ABC):
    # noinspection PyUnusedLocal
    @final
    @static_provision_action(OutputFFRequest)
    def _provide_output_fields_figure(self, mediator: Mediator, request: OutputFFRequest) -> OutputFieldsFigure:
        return self._get_output_fields_figure(request.type)

    @abstractmethod
    def _get_output_fields_figure(self, tp) -> OutputFieldsFigure:
        pass


class NamedTupleFieldsProvider(TypeOnlyInputFFProvider, TypeOnlyOutputFFProvider):
    def _get_input_fields_figure(self, tp) -> InputFieldsFigure:
        if not is_named_tuple_class(tp):
            raise CannotProvide

        return get_func_iff(tp.__new__, slice(1, None))

    def _get_output_fields_figure(self, tp) -> OutputFieldsFigure:
        return OutputFieldsFigure(
            fields=[
                FieldRM(
                    field_name=fld.field_name,
                    type=fld.type,
                    default=fld.default,
                    is_required=True,
                    metadata=fld.metadata,
                )
                for fld in self._get_input_fields_figure(tp).fields
            ],
            getter_kind=GetterKind.ATTR,
        )


def _to_inp(param_kind: ParamKind, fields: List[FieldRM]) -> List[InputFieldRM]:
    return [
        InputFieldRM(
            field_name=f.field_name,
            type=f.type,
            default=f.default,
            is_required=f.is_required,
            metadata=f.metadata,
            param_kind=param_kind,
        )
        for f in fields
    ]


class TypedDictFieldsProvider(TypeOnlyInputFFProvider, TypeOnlyOutputFFProvider):
    def _get_fields(self, tp):
        if not is_typed_dict_class(tp):
            raise CannotProvide

        is_required = tp.__total__

        return [
            FieldRM(
                type=tp,
                field_name=name,
                default=NoDefault(),
                is_required=is_required,
                metadata=MappingProxyType({}),
            )
            for name, tp in get_type_hints(tp).items()
        ]

    def _get_input_fields_figure(self, tp):
        return InputFieldsFigure(
            fields=_to_inp(ParamKind.KW_ONLY, self._get_fields(tp)),
            extra=None,
        )

    def _get_output_fields_figure(self, tp):
        return OutputFieldsFigure(
            fields=self._get_fields(tp),  # noqa
            getter_kind=GetterKind.ITEM,
        )


def get_dc_default(field: DCField) -> Default:
    if field.default is not DC_MISSING:
        return DefaultValue(field.default)
    if field.default_factory is not DC_MISSING:
        return DefaultFactory(field.default_factory)
    return NoDefault()


class DataclassFieldsProvider(TypeOnlyInputFFProvider, TypeOnlyOutputFFProvider):
    """This provider does not work properly if __init__ signature differs from
    that would be created by dataclass decorator.

    It happens because we can not distinguish __init__ that generated
    by @dataclass and __init__ that created by other ways.
    And we can not analyze only __init__ signature
    because @dataclass uses private constant
    as default value for fields with default_factory
    """

    def _get_fields_filtered(self, tp, filer_func, all_are_required: bool):
        if not is_dataclass(tp):
            raise CannotProvide

        return [
            FieldRM(
                type=fld.type,
                field_name=fld.name,
                default=get_dc_default(fld),
                is_required=all_are_required or get_dc_default(fld) == NoDefault(),
                metadata=fld.metadata,
            )
            for fld in dc_fields(tp)
            if filer_func(fld)
        ]

    def _get_input_fields_figure(self, tp):
        return InputFieldsFigure(
            fields=_to_inp(
                ParamKind.POS_OR_KW,
                self._get_fields_filtered(
                    tp, lambda fld: fld.init,
                    all_are_required=False,
                )
            ),
            extra=None,
        )

    def _get_output_fields_figure(self, tp):
        return OutputFieldsFigure(
            fields=self._get_fields_filtered(
                tp, lambda fld: True,
                all_are_required=True,
            ),
            getter_kind=GetterKind.ATTR
        )


class ClassInitFieldsProvider(TypeOnlyInputFFProvider):
    def _get_input_fields_figure(self, tp):
        if not isinstance(tp, type):
            raise CannotProvide

        try:
            return get_func_iff(
                tp.__init__, slice(1, None)
            )
        except ValueError:
            raise CannotProvide
