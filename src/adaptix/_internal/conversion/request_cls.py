from dataclasses import dataclass
from inspect import Signature
from itertools import chain, islice
from typing import Callable, Iterator, Optional, Union

from ..common import Coercer, VarTuple
from ..datastructures import ImmutableStack
from ..model_tools.definitions import BaseField, InputField, OutputField
from ..provider.essential import Request
from ..provider.fields import base_field_to_loc_map, input_field_to_loc_map, output_field_to_loc_map
from ..provider.request_cls import LocatedRequest, LocStack

LinkingSourceItem = Union[OutputField, BaseField]


class LinkingSource(ImmutableStack[LinkingSourceItem]):
    def to_loc_stack(self) -> LocStack:
        return LocStack.from_iter(
            chain(
                (base_field_to_loc_map(self.head), ),
                map(output_field_to_loc_map, self.tail)
            )
        )

    @property
    def head(self) -> BaseField:
        return self[0]

    @property
    def tail(self) -> Iterator[OutputField]:
        return islice(self, 1, None)  # type: ignore[arg-type]


class LinkingDest(ImmutableStack[InputField]):
    def to_loc_stack(self) -> LocStack:
        return LocStack.from_iter(map(input_field_to_loc_map, self))


@dataclass(frozen=True)
class LinkingResult:
    source: LinkingSource
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
class UnlinkedOptionalPolicyRequest(LocatedRequest):
    pass


@dataclass(frozen=True)
class ConverterRequest(Request):
    signature: Signature
    function_name: Optional[str]
    stub_function: Optional[Callable]
