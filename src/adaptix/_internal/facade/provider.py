from __future__ import annotations

from enum import Enum, EnumMeta
from types import MappingProxyType
from typing import Any, Callable, Iterable, List, Mapping, Optional, Sequence, TypeVar, Union

from ..common import Catchable, Dumper, Loader, TypeHint, VarTuple
from ..essential import Provider
from ..load_error import LoadError, ValidationError
from ..model_tools.definitions import Default, DescriptorAccessor, NoDefault, OutputField
from ..model_tools.introspection import get_callable_shape
from ..provider.enum_provider import EnumExactValueProvider, EnumNameProvider, EnumValueProvider
from ..provider.model.loader_provider import InlinedShapeModelLoaderProvider
from ..provider.model.shape_provider import PropertyAdder
from ..provider.model.special_cases_optimization import as_is_stub
from ..provider.name_layout.base import ExtraIn, ExtraOut
from ..provider.name_layout.component import ExtraMoveAndPoliciesOverlay, SievesOverlay, StructureOverlay
from ..provider.name_layout.name_mapping import (
    ConstNameMappingProvider,
    DictNameMappingProvider,
    FuncNameMappingProvider,
    NameMap,
)
from ..provider.name_style import NameStyle
from ..provider.overlay_schema import OverlayProvider
from ..provider.provider_template import ValueProvider
from ..provider.provider_wrapper import BoundingProvider, Chain, ChainingProvider
from ..provider.request_cls import DumperRequest, LoaderRequest
from ..provider.request_filtering import (
    AnyRequestChecker,
    OrRequestChecker,
    Pred,
    RequestChecker,
    RequestPattern,
    create_request_checker,
)
from ..utils import Omittable, Omitted

T = TypeVar('T')


def bound(pred: Pred, provider: Provider) -> Provider:
    if pred == Omitted():
        return provider
    return BoundingProvider(create_request_checker(pred), provider)


def make_chain(chain: Optional[Chain], provider: Provider) -> Provider:
    if chain is None:
        return provider

    return ChainingProvider(chain, provider)


def loader(pred: Pred, func: Loader, chain: Optional[Chain] = None) -> Provider:
    """Basic provider to define custom loader.

    :param pred: Predicate specifying where loader should be used. See :ref:`predicate-system` for details.
    :param func: Function that acts as loader.
        It must take one positional argument of raw data and return the processed value.
    :param chain: Controls how the function will interact with the previous loader.

        When ``None`` is passed, the specified function will fully replace the previous loader.

        If a parameter is ``Chain.FIRST``,
        the specified function will take raw data and its result will be passed to previous loader.

        If the parameter is ``Chain.LAST``, the specified function gets result of the previous loader.

    :return: desired provider
    """
    return bound(
        pred,
        make_chain(
            chain,
            ValueProvider(LoaderRequest, func)
        )
    )


def dumper(pred: Pred, func: Dumper, chain: Optional[Chain] = None) -> Provider:
    """Basic provider to define custom dumper.

    :param pred: Predicate specifying where dumper should be used. See :ref:`predicate-system` for details.
    :param func: Function that acts as dumper.
        It must take one positional argument of raw data and return the processed value.
    :param chain: Controls how the function will interact with the previous dumper.

        When ``None`` is passed, the specified function will fully replace the previous dumper.

        If a parameter is ``Chain.FIRST``,
        the specified function will take raw data and its result will be passed to previous dumper.

        If the parameter is ``Chain.LAST``, the specified function gets result of the previous dumper.

    :return: desired provider
    """
    return bound(
        pred,
        make_chain(
            chain,
            ValueProvider(DumperRequest, func),
        ),
    )


def as_is_loader(pred: Pred) -> Provider:
    """Provider that creates loader which does nothing with input data.

    :param pred: Predicate specifying where loader should be used. See :ref:`predicate-system` for details.
    :return: desired provider
    """
    return loader(pred, as_is_stub)


def as_is_dumper(pred: Pred) -> Provider:
    """Provider that creates dumper which does nothing with input data.

    :param pred: Predicate specifying where dumper should be used. See :ref:`predicate-system` for details.
    :return: desired provider
    """
    return dumper(pred, as_is_stub)


def constructor(pred: Pred, func: Callable) -> Provider:
    input_shape = get_callable_shape(func).input
    return bound(
        pred,
        InlinedShapeModelLoaderProvider(shape=input_shape),
    )


def _name_mapping_convert_map(name_map: Omittable[NameMap]) -> VarTuple[Provider]:
    if isinstance(name_map, Omitted):
        return ()
    if isinstance(name_map, Mapping):
        return (
            DictNameMappingProvider(name_map),
        )
    result: List[Provider] = []
    for element in name_map:
        if isinstance(element, Provider):
            result.append(element)
        elif isinstance(element, Mapping):
            result.append(
                DictNameMappingProvider(element)
            )
        else:
            pred, value = element
            result.append(
                FuncNameMappingProvider(create_request_checker(pred), value)
                if callable(value) else
                ConstNameMappingProvider(create_request_checker(pred), value)
            )
    return tuple(result)


def _name_mapping_convert_preds(value: Omittable[Union[Iterable[Pred], Pred]]) -> Omittable[RequestChecker]:
    if isinstance(value, Omitted):
        return value
    if isinstance(value, Iterable) and not isinstance(value, str):
        return OrRequestChecker([create_request_checker(el) for el in value])
    return create_request_checker(value)


def _name_mapping_convert_omit_default(
    value: Omittable[Union[Iterable[Pred], Pred, bool]]
) -> Omittable[RequestChecker]:
    if isinstance(value, bool):
        return AnyRequestChecker() if value else ~AnyRequestChecker()
    return _name_mapping_convert_preds(value)


def name_mapping(
    pred: Omittable[Pred] = Omitted(),
    *,
    # filtering which fields are presented
    skip: Omittable[Union[Iterable[Pred], Pred]] = Omitted(),
    only: Omittable[Union[Iterable[Pred], Pred]] = Omitted(),
    # mutating names of presented fields
    map: Omittable[NameMap] = Omitted(),  # noqa: A002
    as_list: Omittable[bool] = Omitted(),
    trim_trailing_underscore: Omittable[bool] = Omitted(),
    name_style: Omittable[Optional[NameStyle]] = Omitted(),
    # filtering of dumped data
    omit_default: Omittable[Union[Iterable[Pred], Pred, bool]] = Omitted(),
    # policy for data that does not map to fields
    extra_in: Omittable[ExtraIn] = Omitted(),
    extra_out: Omittable[ExtraOut] = Omitted(),
    # chaining with next matching provider
    chain: Optional[Chain] = Chain.FIRST,
) -> Provider:
    """A name mapping decides which fields will be presented
    to the outside world and how they will look.

    The mapping process consists of two stages:
    1. Determining which fields are presented
    2. Mutating names of presented fields

    `skip` parameter has higher priority than `only`.

    Mutating parameters works in that way:
    Mapper tries to use the value from the map.
    If the field is not presented in the map,
    trim trailing underscore and convert name style.

    The field must follow snake_case to could be converted.

    :param only:
    :param pred:
    :param skip:
    :param map:
    :param as_list:
    :param trim_trailing_underscore:
    :param name_style:
    :param omit_default:
    :param extra_in:
    :param extra_out:
    :param chain:
    """
    return bound(
        pred,
        OverlayProvider(
            overlays=[
                StructureOverlay(
                    skip=_name_mapping_convert_preds(skip),
                    only=_name_mapping_convert_preds(only),
                    map=_name_mapping_convert_map(map),
                    trim_trailing_underscore=trim_trailing_underscore,
                    name_style=name_style,
                    as_list=as_list,
                ),
                SievesOverlay(
                    omit_default=_name_mapping_convert_omit_default(omit_default),
                ),
                ExtraMoveAndPoliciesOverlay(
                    extra_in=extra_in,
                    extra_out=extra_out,
                ),
            ],
            chain=chain,
        )
    )


NameOrProp = Union[str, property]


def add_property(
    pred: Pred,
    prop: NameOrProp,
    tp: Omittable[TypeHint] = Omitted(),
    /, *,
    default: Default = NoDefault(),
    access_error: Optional[Catchable] = None,
    metadata: Mapping[Any, Any] = MappingProxyType({}),
) -> Provider:
    attr_name = _ensure_attr_name(prop)

    field = OutputField(
        id=attr_name,
        type=tp,
        accessor=DescriptorAccessor(attr_name, access_error),
        default=default,
        metadata=metadata,
        original=None,
    )

    return bound(
        pred,
        PropertyAdder(
            output_fields=[field],
            infer_types_for=[field.id] if tp == Omitted() else [],
        )
    )


def _ensure_attr_name(prop: NameOrProp) -> str:
    if isinstance(prop, str):
        return prop

    fget = prop.fget
    if fget is None:
        raise ValueError(f"Property {prop} has no fget")

    return fget.__name__


EnumPred = Union[TypeHint, str, EnumMeta, RequestPattern]


def _wrap_enum_provider(preds: Sequence[EnumPred], provider: Provider) -> Provider:
    if len(preds) == 0:
        return provider

    if Enum in preds:
        raise ValueError(f"Can not apply enum provider to {Enum}")

    return BoundingProvider(
        OrRequestChecker([create_request_checker(pred) for pred in preds]),
        provider,
    )


def enum_by_name(*preds: EnumPred) -> Provider:
    """Provider that represents enum members to the outside world by their name.

    :param preds: Predicates specifying where the provider should be used.
        The provider will be applied if any predicates meet the conditions,
        if no predicates are passed, the provider will be used for all Enums.
        See :ref:`predicate-system` for details.
    :return: desired provider
    """
    return _wrap_enum_provider(preds, EnumNameProvider())


def enum_by_exact_value(*preds: EnumPred) -> Provider:
    """Provider that represents enum members to the outside world by their value without any processing.

    :param preds: Predicates specifying where the provider should be used.
        The provider will be applied if any predicates meet the conditions,
        if no predicates are passed, the provider will be used for all Enums.
        See :ref:`predicate-system` for details.
    :return: desired provider
    """
    return _wrap_enum_provider(preds, EnumExactValueProvider())


def enum_by_value(first_pred: EnumPred, /, *preds: EnumPred, tp: TypeHint) -> Provider:
    """Provider that represents enum members to the outside world by their value by loader and dumper of specified type.
    The loader will call the loader of the :paramref:`tp` and pass it to the enum constructor.
    The dumper will get value from eum member and pass it to the dumper of the :paramref:`tp`.

    :param first_pred: Predicate specifying where the provider should be used.
        See :ref:`predicate-system` for details.
    :param preds: Additional predicates. The provider will be applied if any predicates meet the conditions.
    :param tp: Type of enum members.
        This type must cover all enum members for the correct operation of loader and dumper
    :return: desired provider
    """
    return _wrap_enum_provider([first_pred, *preds], EnumValueProvider(tp))


def validator(
    pred: Pred,
    func: Callable[[Any], bool],
    error: Union[str, Callable[[Any], LoadError], None] = None,
    chain: Chain = Chain.LAST,
) -> Provider:
    # pylint: disable=C3001
    exception_factory = (
        (lambda x: ValidationError(error, x))
        if error is None or isinstance(error, str) else
        error
    )

    def validating_loader(data):
        if func(data):
            return data
        raise exception_factory(data)

    return loader(pred, validating_loader, chain)
