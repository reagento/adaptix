from abc import ABC, abstractmethod
from typing import Iterable

from ..provider.essential import CannotProvide, Mediator
from ..provider.loc_stack_filtering import LocStackChecker
from ..provider.static_provider import StaticProvider, static_provision_action
from .request_cls import BindingRequest, BindingResult, BindingSource, SourceCandidates


class BindingProvider(StaticProvider, ABC):
    @static_provision_action
    @abstractmethod
    def _provide_binder(self, mediator: Mediator, request: BindingRequest) -> BindingResult:
        ...


def iterate_source_candidates(candidates: SourceCandidates) -> Iterable[BindingSource]:
    for source in reversed(candidates):
        if isinstance(source, tuple):
            yield from source
        else:
            yield source


class SameNameBindingProvider(BindingProvider):
    def __init__(self, is_default: bool):
        self._is_default = is_default

    def _provide_binder(self, mediator: Mediator, request: BindingRequest) -> BindingResult:
        target_field_id = request.destination.last.id
        for source in iterate_source_candidates(request.sources):
            if source.last.id == target_field_id:
                return BindingResult(source=source, is_default=self._is_default)
        raise CannotProvide


class MatchingBindingProvider(BindingProvider):
    def __init__(self, src_lsc: LocStackChecker, dst_lsc: LocStackChecker):
        self._src_lsc = src_lsc
        self._dst_lsc = dst_lsc

    def _provide_binder(self, mediator: Mediator, request: BindingRequest) -> BindingResult:
        if not self._dst_lsc.check_loc_stack(mediator, request.destination.to_loc_stack()):
            raise CannotProvide

        for source in iterate_source_candidates(request.sources):
            if self._src_lsc.check_loc_stack(mediator, source.to_loc_stack()):
                return BindingResult(source=source)
        raise CannotProvide
