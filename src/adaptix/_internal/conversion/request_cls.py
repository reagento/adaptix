from dataclasses import dataclass
from inspect import Signature
from itertools import islice
from typing import Callable, Iterator, Optional, Union

from ..common import Coercer, VarTuple
from ..model_tools.definitions import DefaultFactory, DefaultValue
from ..provider.essential import Request
from ..provider.location import FieldLoc, GenericParamLoc, InputFieldLoc, OutputFieldLoc, TypeHintLoc
from ..provider.request_cls import LocatedRequest, LocStack

LinkingSourceItem = Union[FieldLoc, OutputFieldLoc, GenericParamLoc]


class LinkingSource(LocStack[LinkingSourceItem]):
    @property
    def head(self) -> FieldLoc:
        return next(iter(self))  # type: ignore[return-value]

    @property
    def tail(self) -> Iterator[OutputFieldLoc]:
        return islice(self, 1, None)  # type: ignore[arg-type]

    @property
    def last_field_id(self) -> Optional[str]:
        try:
            return self.last.field_id  # type: ignore[union-attr]
        except AttributeError:
            return None


LinkingDestItem = Union[TypeHintLoc, InputFieldLoc, GenericParamLoc]


class LinkingDest(LocStack[LinkingDestItem]):
    @property
    def last_field_id(self) -> Optional[str]:
        try:
            return self.last.field_id  # type: ignore[union-attr]
        except AttributeError:
            return None


@dataclass(frozen=True)
class FieldLinking:
    source: LinkingSource
    coercer: Optional[Coercer]


@dataclass(frozen=True)
class ConstantLinking:
    constant: Union[DefaultValue, DefaultFactory]


@dataclass(frozen=True)
class LinkingResult:
    linking: Union[FieldLinking, ConstantLinking]
    is_default: bool = False


SourceCandidates = VarTuple[Union[LinkingSource, VarTuple[LinkingSource]]]


@dataclass(frozen=True)
class LinkingRequest(Request[LinkingResult]):
    sources: SourceCandidates
    destination: LinkingDest


@dataclass(frozen=True)
class CoercerRequest(Request[Coercer]):
    src: LinkingSource
    dst: LinkingDest


@dataclass(frozen=True)
class UnlinkedOptionalPolicy:
    is_allowed: bool


@dataclass(frozen=True)
class UnlinkedOptionalPolicyRequest(LocatedRequest[UnlinkedOptionalPolicy]):
    pass


@dataclass(frozen=True)
class ConverterRequest(Request):
    signature: Signature
    function_name: Optional[str]
    stub_function: Optional[Callable]
