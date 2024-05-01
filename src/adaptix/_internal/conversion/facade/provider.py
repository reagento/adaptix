from typing import AbstractSet, Any, Callable, Iterable, Optional, Union, overload

from ...common import OneArgCoercer
from ...model_tools.definitions import DefaultFactory, DefaultValue
from ...provider.essential import Provider
from ...provider.facade.provider import bound_by_any
from ...provider.loc_stack_filtering import LocStackChecker, Pred, create_loc_stack_checker
from ..coercer_provider import MatchingCoercerProvider
from ..linking_provider import ConstantLinkingProvider, FunctionLinkingProvider, MatchingLinkingProvider
from ..policy_provider import UnlinkedOptionalPolicyProvider
from ..request_filtering import FromCtxParam


def link(src: Pred, dst: Pred, *, coercer: Optional[OneArgCoercer] = None) -> Provider:
    """Basic provider to define custom linking between fields.

    :param src: Predicate specifying source point of linking. See :ref:`predicate-system` for details.
    :param dst: Predicate specifying destination point of linking. See :ref:`predicate-system` for details.
    :param coercer: Function transforming source value to target.
        It has higher priority than generic coercers defined by :func:`.coercer`.
    :return: Desired provider
    """
    return MatchingLinkingProvider(
        src_lsc=create_loc_stack_checker(src),
        dst_lsc=create_loc_stack_checker(dst),
        coercer=coercer,
    )


@overload
def link_constant(dst: Pred, *, value: Any) -> Provider:
    ...


@overload
def link_constant(dst: Pred, *, factory: Callable[[], Any]) -> Provider:
    ...


def link_constant(dst: Pred, *, value: Any = None, factory: Any = None) -> Provider:
    """Provider that passes a constant value or the result of a function call to a field.

    :param dst: Predicate specifying destination point of linking. See :ref:`predicate-system` for details.
    :param value: A value is passed to the field.
    :param factory: A callable producing value passed to the field.
    :return: Desired provider
    """
    return ConstantLinkingProvider(
        create_loc_stack_checker(dst),
        DefaultFactory(factory) if factory is not None else DefaultValue(value),
    )


def _ensure_str_set(value: Union[str, Iterable[str]]) -> AbstractSet[str]:
    if isinstance(value, str):
        return frozenset([value])
    return frozenset(value)


def link_function(
    func: Callable,
    dst: Pred,
    *,
    pass_model: Union[str, Iterable[str]] = (),
    pass_params: Union[str, Iterable[str]] = (),
) -> Provider:
    """Provider that uses function to produce value of destination field.
    Each parameter of the function is linked to the source model field by name.
    You can link the model entirely via `pass_model` or link converter parameters via `pass_params`.

    :param func: A function using to process several fields of source model.
    :param dst: Predicate specifying destination point of linking. See :ref:`predicate-system` for details.
    :param pass_model: Mark function parameters to take model entirely.
    :param pass_params: Mark function parameters to take parameters from converter.
    :return: Desired provider
    """
    return FunctionLinkingProvider(
        func=func,
        dst_lsc=create_loc_stack_checker(dst),
        pass_model=_ensure_str_set(pass_model),
        pass_params=_ensure_str_set(pass_params),
    )


def coercer(src: Pred, dst: Pred, func: OneArgCoercer) -> Provider:
    """Basic provider to define custom coercer.

    :param src: Predicate specifying source point of linking. See :ref:`predicate-system` for details.
    :param dst: Predicate specifying destination point of linking. See :ref:`predicate-system` for details.
    :param func: The function is used to transform input data to a destination type.
    :return: Desired provider
    """
    return MatchingCoercerProvider(
        src_lsc=create_loc_stack_checker(src),
        dst_lsc=create_loc_stack_checker(dst),
        coercer=func,
    )


def allow_unlinked_optional(*preds: Pred) -> Provider:
    """Sets policy to permit optional fields that does not linked to any source field.

    :param preds: Predicate specifying target of policy.
        Each predicate is merged via ``|`` operator.
        See :ref:`predicate-system` for details.
    :return: Desired provider.
    """
    return bound_by_any(preds, UnlinkedOptionalPolicyProvider(is_allowed=True))


def forbid_unlinked_optional(*preds: Pred) -> Provider:
    """Sets policy to prohibit optional fields that does not linked to any source field.

    :param preds: Predicate specifying target of policy.
        Each predicate is merged via ``|`` operator.
        See :ref:`predicate-system` for details.
    :return: Desired provider.
    """
    return bound_by_any(preds, UnlinkedOptionalPolicyProvider(is_allowed=False))


def from_param(param_name: str) -> LocStackChecker:
    """The special predicate form matching only top-level parameters by name"""
    return FromCtxParam(param_name)
