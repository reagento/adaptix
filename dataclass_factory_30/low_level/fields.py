from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Union

from ..core import ProvisionCtx


@dataclass(frozen=True)
class DefaultValue:
    value: Any


@dataclass(frozen=True)
class DefaultFactory:
    factory: Callable[[], Any]


Default = Union[None, DefaultValue, DefaultFactory]


@dataclass(frozen=True)
class FieldsProvisionCtx(ProvisionCtx):
    field_name: str
    field_in_init: bool
    default: Default
    metadata: MappingProxyType
