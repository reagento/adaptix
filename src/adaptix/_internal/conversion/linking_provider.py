from abc import ABC, abstractmethod
from typing import Iterable, Optional, Union

from ..common import Coercer
from ..model_tools.definitions import DefaultFactory, DefaultValue
from ..provider.essential import CannotProvide, Mediator
from ..provider.loc_stack_filtering import LocStackChecker
from ..provider.static_provider import StaticProvider, static_provision_action
from .request_cls import ConstantLinking, FieldLinking, LinkingRequest, LinkingResult, LinkingSource, SourceCandidates


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
    def __init__(self, *, is_default: bool):
        self._is_default = is_default

    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        target_field_id = request.destination.last_field_id
        for source in iterate_source_candidates(request.sources):
            if source.last_field_id == target_field_id:
                return LinkingResult(
                    linking=FieldLinking(source=source, coercer=None),
                    is_default=self._is_default,
                )
        raise CannotProvide


class MatchingLinkingProvider(LinkingProvider):
    def __init__(self, src_lsc: LocStackChecker, dst_lsc: LocStackChecker, coercer: Optional[Coercer]):
        self._src_lsc = src_lsc
        self._dst_lsc = dst_lsc
        self._coercer = coercer

    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        if not self._dst_lsc.check_loc_stack(mediator, request.destination):
            raise CannotProvide

        for source in iterate_source_candidates(request.sources):
            if self._src_lsc.check_loc_stack(mediator, source):
                return LinkingResult(linking=FieldLinking(source=source, coercer=self._coercer))
        raise CannotProvide


class ConstantLinkingProvider(LinkingProvider):
    def __init__(self, dst_lsc: LocStackChecker, default: Union[DefaultValue, DefaultFactory]):
        self._dst_lsc = dst_lsc
        self._default = default

    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        if self._dst_lsc.check_loc_stack(mediator, request.destination):
            return LinkingResult(linking=ConstantLinking(self._default))
        raise CannotProvide
