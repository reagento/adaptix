# pylint: disable=import-outside-toplevel
import typing
from dataclasses import InitVar
from typing import Callable, ClassVar, Final, Tuple

from ..feature_requirement import HAS_ANNOTATED, HAS_TYPE_GUARD
from .normalize_type import BaseNormType, NormTV

_TYPE_TAGS = [Final, ClassVar, InitVar]

if HAS_ANNOTATED:
    _TYPE_TAGS.append(typing.Annotated)

if HAS_TYPE_GUARD:
    _TYPE_TAGS.append(typing.TypeGuard)


def strip_tags(norm: BaseNormType) -> BaseNormType:
    """Removes type hints that does not represent type
    and that only indicates metadata
    """
    if norm.origin in _TYPE_TAGS:
        return strip_tags(norm.args[0])
    return norm


def _tv_or_generic(norm: BaseNormType) -> bool:
    return isinstance(strip_tags(norm), NormTV) or is_generic(norm)


def is_generic(norm: BaseNormType) -> bool:
    st_norm = strip_tags(norm)

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

    args: Tuple
    if st_norm.origin == tuple and st_norm.args[-1] is ...:
        args = (st_norm.args[0],)
    else:
        args = st_norm.args

    return any(
        _tv_or_generic(a) for a in args
    )
