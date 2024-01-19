from abc import ABC, abstractmethod
from typing import final

from ..common import Dumper, Loader, TypeHint
from ..provider.essential import CannotProvide, Mediator
from ..provider.loc_stack_filtering import ExactOriginLSC
from ..provider.provider_template import ProviderWithAttachableLSC
from ..provider.request_cls import TypeHintLoc
from ..provider.static_provider import static_provision_action
from ..type_tools import normalize_type
from .request_cls import DumperRequest, LoaderRequest


class LoaderProvider(ProviderWithAttachableLSC, ABC):
    @final
    @static_provision_action
    def _outer_provide_loader(self, mediator: Mediator, request: LoaderRequest):
        self._apply_loc_stack_checker(mediator, request)
        return self._provide_loader(mediator, request)

    @abstractmethod
    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        ...


class DumperProvider(ProviderWithAttachableLSC, ABC):
    @final
    @static_provision_action
    def _outer_provide_dumper(self, mediator: Mediator, request: DumperRequest):
        self._apply_loc_stack_checker(mediator, request)
        return self._provide_dumper(mediator, request)

    @abstractmethod
    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        ...


class ABCProxy(LoaderProvider, DumperProvider):
    def __init__(self, abstract: TypeHint, impl: TypeHint, for_loader: bool = True, for_dumper: bool = True):
        self._abstract = normalize_type(abstract).origin
        self._impl = impl
        self._loc_stack_checker = ExactOriginLSC(self._abstract)
        self._for_loader = for_loader
        self._for_dumper = for_dumper

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        if not self._for_loader:
            raise CannotProvide

        return mediator.mandatory_provide(
            LoaderRequest(
                loc_stack=request.loc_stack.add_to_last_map(TypeHintLoc(type=self._impl))
            ),
            lambda x: f'Cannot create loader for union. Loader for {self._impl} cannot be created',
        )

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        if not self._for_dumper:
            raise CannotProvide

        return mediator.mandatory_provide(
            DumperRequest(
                loc_stack=request.loc_stack.add_to_last_map(TypeHintLoc(type=self._impl))
            ),
            lambda x: f'Cannot create dumper for union. Dumper for {self._impl} cannot be created',
        )
