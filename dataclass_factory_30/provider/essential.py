from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from typing import TypeVar, Generic, Optional, List, Tuple, Sequence, Type

T = TypeVar('T')


@dataclass(frozen=True)
class Request(Generic[T]):
    """An object that contains data to be processed by Provider.

    Generic argument indicates which object should be
    returned after request processing
    """


@dataclass
class CannotProvide(Exception):
    msg: Optional[str] = None
    sub_errors: Sequence['CannotProvide'] = field(default_factory=list)

    def __post_init__(self):
        Exception.__init__(self)


class Mediator(ABC):
    """Mediator is a object that gives provider access to other providers
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


class PipelineEvalMixin(Request):
    """A special mixin for Request that allows to eval pipeline.
    Subclass should implement :method:`eval_pipeline`
    """

    @classmethod
    @abstractmethod
    def eval_pipeline(
        cls: Type[Request[T]],
        providers: List[Provider],
        mediator: Mediator,
        request: Request[T]
    ) -> T:
        pass


class Pipeline(Provider):
    def __init__(self, elements: Tuple[Provider, ...]):
        self.elements = elements

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        if not isinstance(request, PipelineEvalMixin):
            raise CannotProvide

        return request.eval_pipeline(
            list(self.elements), mediator, request
        )

    def __or__(self, other: Provider):
        if isinstance(other, Pipeline):
            return Pipeline(self.elements + other.elements)
        return Pipeline(self.elements + (other,))
