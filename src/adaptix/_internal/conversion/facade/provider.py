from ...common import Coercer
from ...provider.essential import Provider
from ...provider.loc_stack_filtering import Pred, create_loc_stack_checker
from ..binding_provider import MatchingBindingProvider
from ..coercer_provider import MatchingCoercerProvider


def bind(src: Pred, dst: Pred) -> Provider:
    return MatchingBindingProvider(
        src_lsc=create_loc_stack_checker(src),
        dst_lsc=create_loc_stack_checker(dst),
    )


def coercer(src: Pred, dst: Pred, func: Coercer) -> Provider:
    return MatchingCoercerProvider(
        src_lsc=create_loc_stack_checker(src),
        dst_lsc=create_loc_stack_checker(dst),
        coercer=func,
    )
