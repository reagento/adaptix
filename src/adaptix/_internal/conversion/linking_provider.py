from abc import ABC, abstractmethod
from typing import Iterable

from ..provider.essential import CannotProvide, Mediator
from ..provider.loc_stack_filtering import LocStackChecker
from ..provider.static_provider import StaticProvider, static_provision_action
from .request_cls import LinkingRequest, LinkingResult, LinkingSource, SourceCandidates


class LinkingProvider(StaticProvider, ABC):
    @static_provision_action
    @abstractmethod
    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        ...


def iterate_source_candidates(candidates: SourceCandidates) -> Iterable[LinkingSource]:
    for source in reversed(candidates):
        if isinstance(source, tuple):
            yield from source
        else:
            yield source


class SameNameLinkingProvider(LinkingProvider):
    def __init__(self, is_default: bool):
        self._is_default = is_default

    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        target_field_id = request.destination.last.id
        for source in iterate_source_candidates(request.sources):
            if source.last.id == target_field_id:
                return LinkingResult(source=source, is_default=self._is_default)
        raise CannotProvide


class MatchingLinkingProvider(LinkingProvider):
    def __init__(self, src_lsc: LocStackChecker, dst_lsc: LocStackChecker):
        self._src_lsc = src_lsc
        self._dst_lsc = dst_lsc

    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        if not self._dst_lsc.check_loc_stack(mediator, request.destination.to_loc_stack()):
            raise CannotProvide

        for source in iterate_source_candidates(request.sources):
            if self._src_lsc.check_loc_stack(mediator, source.to_loc_stack()):
                return LinkingResult(source=source)
        raise CannotProvide
