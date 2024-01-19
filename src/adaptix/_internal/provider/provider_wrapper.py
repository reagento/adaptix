from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Type, TypeVar

from .essential import AggregateCannotProvide, CannotProvide, Mediator, Provider, Request
from .loc_stack_filtering import LocStackChecker
from .request_cls import LocatedRequest

T = TypeVar('T')


class RequestClassDeterminedProvider(Provider, ABC):
    @abstractmethod
    def maybe_can_process_request_cls(self, request_cls: Type[Request]) -> bool:
        ...


class ProviderWithLSC(Provider, ABC):
    @abstractmethod
    def get_loc_stack_checker(self) -> Optional[LocStackChecker]:
        ...

    def _apply_loc_stack_checker(self, mediator: Mediator, request: Request) -> None:
        if not isinstance(request, LocatedRequest):
            raise CannotProvide

        loc_stack_checker = self.get_loc_stack_checker()
        if loc_stack_checker is None:
            return

        if not loc_stack_checker.check_loc_stack(mediator, request.loc_stack):
            raise CannotProvide


class BoundingProvider(RequestClassDeterminedProvider, ProviderWithLSC):
    def __init__(self, loc_stack_checker: LocStackChecker, provider: Provider):
        self._loc_stack_checker = loc_stack_checker
        self._provider = provider

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        self._apply_loc_stack_checker(mediator, request)
        return self._provider.apply_provider(mediator, request)

    def __repr__(self):
        return f"{type(self).__name__}({self._loc_stack_checker}, {self._provider})"

    def maybe_can_process_request_cls(self, request_cls: Type[Request]) -> bool:
        if isinstance(self._provider, RequestClassDeterminedProvider):
            return self._provider.maybe_can_process_request_cls(request_cls)
        return True

    def get_loc_stack_checker(self) -> Optional[LocStackChecker]:
        return self._loc_stack_checker


class ConcatProvider(RequestClassDeterminedProvider):
    def __init__(self, *providers: Provider):
        self._providers = providers

    def apply_provider(self, mediator: Mediator[T], request: Request[T]) -> T:
        exceptions = []

        for provider in self._providers:
            try:
                return provider.apply_provider(mediator, request)
            except CannotProvide as e:
                exceptions.append(e)

        raise AggregateCannotProvide.make('', exceptions)

    def __repr__(self):
        return f"{type(self).__name__}({self._providers})"

    def maybe_can_process_request_cls(self, request_cls: Type[Request]) -> bool:
        return any(
            not isinstance(provider, RequestClassDeterminedProvider)
            or provider.maybe_can_process_request_cls(request_cls)
            for provider in self._providers
        )


class Chain(Enum):
    FIRST = 'FIRST'
    LAST = 'LAST'


class ChainingProvider(RequestClassDeterminedProvider):
    def __init__(self, chain: Chain, provider: Provider):
        self._chain = chain
        self._provider = provider

    def apply_provider(self, mediator: Mediator[T], request: Request[T]) -> T:
        current_processor = self._provider.apply_provider(mediator, request)
        next_processor = mediator.provide_from_next()

        if self._chain == Chain.FIRST:
            return self._make_chain(current_processor, next_processor)
        if self._chain == Chain.LAST:
            return self._make_chain(next_processor, current_processor)
        raise ValueError

    def _make_chain(self, first, second):
        def chain_processor(data):
            return second(first(data))

        return chain_processor

    def maybe_can_process_request_cls(self, request_cls: Type[Request]) -> bool:
        if isinstance(self._provider, RequestClassDeterminedProvider):
            return self._provider.maybe_can_process_request_cls(request_cls)
        return True
