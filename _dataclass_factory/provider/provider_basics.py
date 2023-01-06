from enum import Enum
from typing import Generic, Type, TypeVar

from .essential import CannotProvide, Mediator, Provider, Request
from .request_filtering import RequestChecker

T = TypeVar('T')


class BoundingProvider(Provider):
    def __init__(self, request_checker: RequestChecker, provider: Provider):
        self._request_checker = request_checker
        self._provider = provider

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        self._request_checker.check_request(mediator, request)
        return self._provider.apply_provider(mediator, request)

    def __repr__(self):
        return f"{type(self).__name__}({self._request_checker}, {self._provider})"


class ValueProvider(Provider, Generic[T]):
    def __init__(self, request_cls: Type[Request[T]], value: T):
        self._request_cls = request_cls
        self._value = value

    def apply_provider(self, mediator: Mediator, request: Request):
        if not isinstance(request, self._request_cls):
            raise CannotProvide

        return self._value

    def __repr__(self):
        return f"{type(self).__name__}({self._request_cls}, {self._value})"


class ConcatProvider(Provider):
    def __init__(self, *providers: Provider):
        self._providers = providers

    def apply_provider(self, mediator: Mediator[T], request: Request[T]) -> T:
        errors = []

        for provider in self._providers:
            try:
                return provider.apply_provider(mediator, request)
            except CannotProvide as e:
                errors.append(e)

        raise CannotProvide(sub_errors=errors)

    def __repr__(self):
        return f"{type(self).__name__}({self._providers})"


class Chain(Enum):
    FIRST = 'FIRST'
    LAST = 'LAST'


class ChainingProvider(Provider):
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
