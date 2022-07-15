from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Iterable, Optional, Sequence, Type, TypeVar

from ..common import VarTuple

T = TypeVar('T')


@dataclass(frozen=True)
class Request(Generic[T]):
    """An object that contains data to be processed by Provider.

    Generic argument indicates which object should be
    returned after request processing.

    Request must be always a hashable object
    """


class CannotProvide(Exception):
    def __init__(
        self,
        msg: Optional[str] = None,
        sub_errors: Optional[Sequence['CannotProvide']] = None,
        is_important: bool = False,
    ):
        """
        :param msg: Human-oriented description of error
        :param sub_errors: Errors caused this error
        :param is_important: if the error is important,
            it will be propagated above and the following providers will not be tested
        """
        if sub_errors is None:
            sub_errors = []
        self.msg = msg
        self.sub_errors = sub_errors
        self._is_important = is_important

    def __eq__(self, other):
        if isinstance(other, CannotProvide):
            return (
                self.msg == other.msg
                and self.sub_errors == other.sub_errors
                and self._is_important == other._is_important
            )
        return NotImplemented

    # TODO: maybe add checking of __cause__ and __context__
    def is_important(self) -> bool:
        return self._is_important or any(error.is_important for error in self.sub_errors)

    def __repr__(self):
        content = f"msg={self.msg!r}, sub_errors={self.sub_errors!r}, is_important={self._is_important!r}"
        return f"{type(self).__name__}({content})"


class Mediator(ABC):
    """Mediator is an object that gives provider access to other providers
    and that stores state of the current search.

    Mediator is a proxy to providers of factory.
    """

    @abstractmethod
    def provide(self, request: Request[T]) -> T:
        """Get response of sent request.
        :param request: A request instance
        :return: Result of the request processing
        :raise CannotProvide: A provider able to process the request does not found
        """
        raise NotImplementedError

    @abstractmethod
    def provide_from_next(self, request: Request[T]) -> T:
        """Same as :method provide: but it skips themself
        and providers already tested at this iteration.
        """
        raise NotImplementedError


class Provider(ABC):
    """An object that can process Request instances"""

    @abstractmethod
    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        """Handle request instance and return a value of type required by request.
        Behavior must be the same during the provider object lifetime

        :raise CannotProvide: provider cannot process passed request
        """
        raise NotImplementedError

    def __or__(self, other: 'Provider') -> 'Pipeline':
        if isinstance(other, Pipeline):
            return Pipeline((self,) + other.elements)
        return Pipeline((self, other))


class PipelineEvalMixin(Request[T], Generic[T]):
    """A special mixin for Request that allows to eval pipeline.
    Subclass should implement :method:`eval_pipeline`
    """

    @classmethod
    @abstractmethod
    def eval_pipeline(
        cls: Type[Request[T]],
        providers: Iterable[Provider],
        mediator: Mediator,
        request: Request[T]
    ) -> T:
        pass


class Pipeline(Provider):
    def __init__(self, elements: VarTuple[Provider]):
        self._elements = elements

    @property
    def elements(self) -> VarTuple[Provider]:
        return self._elements

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        if not isinstance(request, PipelineEvalMixin):
            raise CannotProvide

        return request.eval_pipeline(
            list(self._elements), mediator, request
        )

    def __or__(self, other: Provider):
        if isinstance(other, Pipeline):
            return Pipeline(self._elements + other._elements)
        return Pipeline(self._elements + (other,))
