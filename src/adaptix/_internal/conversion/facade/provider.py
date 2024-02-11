from ...common import Coercer
from ...provider.essential import Provider
from ...provider.facade.provider import bound_by_any
from ...provider.loc_stack_filtering import Pred, create_loc_stack_checker
from ..binding_provider import MatchingBindingProvider
from ..coercer_provider import MatchingCoercerProvider
from ..policy_provider import UnboundOptionalPolicyProvider


def bind(src: Pred, dst: Pred) -> Provider:
    """Basic provider to define custom binding between fields.

    :param src: Predicate specifying source point of binding. See :ref:`predicate-system` for details.
    :param dst: Predicate specifying destination point of binding. See :ref:`predicate-system` for details.
    :return: Desired provider
    """
    return MatchingBindingProvider(
        src_lsc=create_loc_stack_checker(src),
        dst_lsc=create_loc_stack_checker(dst),
    )


def coercer(src: Pred, dst: Pred, func: Coercer) -> Provider:
    """Basic provider to define custom coercer.

    :param src: Predicate specifying source point of binding. See :ref:`predicate-system` for details.
    :param dst: Predicate specifying destination point of binding. See :ref:`predicate-system` for details.
    :param func: The function is used to transform input data to a destination type.
    :return: Desired provider
    """
    return MatchingCoercerProvider(
        src_lsc=create_loc_stack_checker(src),
        dst_lsc=create_loc_stack_checker(dst),
        coercer=func,
    )


def allow_unbound_optional(*preds: Pred) -> Provider:
    """Sets policy to permit optional fields that does not bound to any source field.

    :param preds: Predicate specifying target of policy.
        Each predicate is merged via ``|`` operator.
        See :ref:`predicate-system` for details.
    :return: Desired provider.
    """
    return bound_by_any(preds, UnboundOptionalPolicyProvider(is_allowed=True))


def forbid_unbound_optional(*preds: Pred) -> Provider:
    """Sets policy to prohibit optional fields that does not bound to any source field.

    :param preds: Predicate specifying target of policy.
        Each predicate is merged via ``|`` operator.
        See :ref:`predicate-system` for details.
    :return: Desired provider.
    """
    return bound_by_any(preds, UnboundOptionalPolicyProvider(is_allowed=False))
