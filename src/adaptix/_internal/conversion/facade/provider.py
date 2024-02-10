from ...common import Coercer
from ...provider.essential import Provider
from ...provider.loc_stack_filtering import Pred, create_loc_stack_checker
from ..binding_provider import MatchingBindingProvider
from ..coercer_provider import MatchingCoercerProvider


def bind(src: Pred, dst: Pred) -> Provider:
    """Basic provider to define custom binding between fields.

    :param src: Predicate specifying source point of binding. See :ref:`predicate-system` for details.
    :param dst: Predicate specifying destination point of binding. See :ref:`predicate-system` for details.
    :return: desired provider
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
    :return: desired provider
    """
    return MatchingCoercerProvider(
        src_lsc=create_loc_stack_checker(src),
        dst_lsc=create_loc_stack_checker(dst),
        coercer=func,
    )
