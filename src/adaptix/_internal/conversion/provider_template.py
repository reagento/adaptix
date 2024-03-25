from abc import ABC, abstractmethod
from typing import Iterable, final

from ..common import Coercer, Converter
from ..provider.essential import Mediator
from ..provider.static_provider import StaticProvider, static_provision_action
from .request_cls import CoercerRequest, ConverterRequest, LinkingRequest, LinkingResult, LinkingSource


class ConverterProvider(StaticProvider, ABC):
    @final
    @static_provision_action
    def _outer_provide_converter(self, mediator: Mediator, request: ConverterRequest):
        return self._provide_converter(mediator, request)

    @abstractmethod
    def _provide_converter(self, mediator: Mediator, request: ConverterRequest) -> Converter:
        ...


class CoercerProvider(StaticProvider, ABC):
    @static_provision_action
    @abstractmethod
    def _provide_coercer(self, mediator: Mediator, request: CoercerRequest) -> Coercer:
        ...


class LinkingProvider(StaticProvider, ABC):
    @static_provision_action
    @abstractmethod
    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        ...


def iterate_source_candidates(request: LinkingRequest) -> Iterable[LinkingSource]:
    yield from reversed(request.context.loc_stacks)
    yield from request.sources
