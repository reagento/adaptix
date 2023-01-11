from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, Optional, Sequence, TypeVar

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
    ):
        """
        :param msg: Human-oriented description of error
        :param sub_errors: Errors caused this error
        """
        if sub_errors is None:
            sub_errors = []
        self.msg = msg
        self.sub_errors = sub_errors
        super().__init__(self.msg, self.sub_errors)

    def __repr__(self):
        return f"{type(self).__name__}(msg={self.msg!r}, sub_errors={self.sub_errors!r})"


V = TypeVar('V')


class Mediator(ABC, Generic[V]):
    """Mediator is an object that gives provider access to other providers
    and that stores state of the current search.

    Mediator is a proxy to providers of retort.
    """

    @abstractmethod
    def provide(self, request: Request[T]) -> T:
        """Get response of sent request.
        :param request: A request instance
        :return: Result of the request processing
        :raise CannotProvide: A provider able to process the request does not found
        """

    @abstractmethod
    def provide_from_next(self) -> V:
        """Forward current request to providers
        that placed after current provider at the recipe.
        """

    @property
    @abstractmethod
    def request_stack(self) -> Sequence[Request[Any]]:
        """Call stack, but consisting of requests.
        Last element of request_stack is current request.
        """


class Provider(ABC):
    """An object that can process Request instances"""

    @abstractmethod
    def apply_provider(self, mediator: Mediator[T], request: Request[T]) -> T:
        """Handle request instance and return a value of type required by request.
        Behavior must be the same during the provider object lifetime

        :raise CannotProvide: provider cannot process passed request
        """
