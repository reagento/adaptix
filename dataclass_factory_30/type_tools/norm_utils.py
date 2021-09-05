from typing import ClassVar, Callable

from .normalize_type import BaseNormType, NormTV
from ..feature_requirement import has_final, has_annotated


def strip_tag(norm: BaseNormType) -> BaseNormType:
    if has_final:
        from typing import Final

        if norm.origin == Final:
            return norm.args[0]

    if has_annotated:
        from typing import Annotated

        if norm.origin == Annotated:
            return norm.args[0]

    if norm.origin == ClassVar:
        return norm.args[0]

    return norm


def _tv_or_generic(norm: BaseNormType) -> bool:
    return isinstance(strip_tag(norm), NormTV) or is_generic(norm)


def is_generic(norm: BaseNormType) -> bool:
    st_norm = strip_tag(norm)

    if st_norm.origin == Callable:
        if st_norm.args[0] is ...:
            call_params = []
        else:
            call_params = st_norm.args[0]

        return (
            any(_tv_or_generic(p) for p in call_params)
            or
            _tv_or_generic(st_norm.args[1])
        )

    if st_norm.origin == tuple and st_norm.args[-1] is ...:
        args = [st_norm.args[0]]
    else:
        args = st_norm.args

    return any(
        _tv_or_generic(a) for a in args
    )
