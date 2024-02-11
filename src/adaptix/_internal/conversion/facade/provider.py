from ...common import Coercer
from ...provider.essential import Provider
from ...provider.facade.provider import bound_by_any
from ...provider.loc_stack_filtering import Pred, create_loc_stack_checker
from ..coercer_provider import MatchingCoercerProvider
from ..linking_provider import MatchingLinkingProvider
from ..policy_provider import UnlinkedOptionalPolicyProvider


def link(src: Pred, dst: Pred) -> Provider:
    """Basic provider to define custom linking between fields.

    :param src: Predicate specifying source point of linking. See :ref:`predicate-system` for details.
    :param dst: Predicate specifying destination point of linking. See :ref:`predicate-system` for details.
    :return: Desired provider
    """
    return MatchingLinkingProvider(
        src_lsc=create_loc_stack_checker(src),
        dst_lsc=create_loc_stack_checker(dst),
    )


def coercer(src: Pred, dst: Pred, func: Coercer) -> Provider:
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
