# pylint: disable=import-outside-toplevel
import typing
from dataclasses import InitVar
from typing import ClassVar, Final

from ..feature_requirement import HAS_ANNOTATED
from .normalize_type import BaseNormType

_TYPE_TAGS = [Final, ClassVar, InitVar]

if HAS_ANNOTATED:
    _TYPE_TAGS.append(typing.Annotated)


def strip_tags(norm: BaseNormType) -> BaseNormType:
    """Removes type hints that does not represent type
    and that only indicates metadata
    """
    if norm.origin in _TYPE_TAGS:
        return strip_tags(norm.args[0])
    return norm
