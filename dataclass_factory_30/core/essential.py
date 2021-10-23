from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from typing import TypeVar, Generic, final, Optional, List, Tuple, Sequence

from .class_dispatcher import ClassDispatcher, ClassDispatcherKeysView

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


RequestDispatcher = ClassDispatcher[Request, str]


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
        :raise NoSuitableProvider: A provider able to process the request does not found
        """
        raise NotImplementedError

    @abstractmethod
    def provide_from_next(self, request: Request[T]) -> T:
        """Same as :method provide: but it skips themself
        and providers already tested at this iteration.
        """
        raise NotImplementedError


class Provider(ABC):
    """A provider is an object that can process Request instances.
    It defines methods called provision action
    that takes 2 arguments (Mediator, Request)
    and returns the expected result or raises CannotProvide.

    Which provision action should be called for a specific request
    is determined by RequestDispatcher obtained from :method get_request_dispatcher:.
    RequestDispatcher is a :class ClassDispatcher: where keys are :class Request:
    classes and values are strings (names of methods).

    ``RequestDispatcher({ParserRequest: "provide_parser"})`` means that Provider object may
    process ParserRequest and it's children. That provision action must never be called with
    other classes of request.

    If the request class is a child of several registered classes
    RequestDispatcher will select the closest parent (defined by MRO).
    So ``RequestDispatcher({ParserRequest: "provide_parser", Request: "provide_other"})``
    means that ParserRequest and it's children will be processed by ``provide_parser``
    and other requests will be processed by ``provide_other``

    RequestDispatcher returned by :method get_request_dispatcher:
    must be the same during the provider object lifetime
    """

    @abstractmethod
    def get_request_dispatcher(self) -> RequestDispatcher:
        raise NotImplementedError

    @final
    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        """This method is suitable wrapper
        around :method get_request_dispatcher: and getattr().
        Factory may not use this method
        implementing own cached provision action call.
        """
        try:
            attr_name = self.get_request_dispatcher().dispatch(type(request))
        except KeyError:
            raise CannotProvide

        return getattr(self, attr_name)(mediator, request)

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
        cls,
        providers: List[Provider],
        mediator: Mediator,
        request: Request
    ):
        pass


class Pipeline(Provider):
    def __init__(self, elements: Tuple[Provider, ...]):
        self.elements = elements
        self._rd: Optional[RequestDispatcher] = None

    def get_request_dispatcher(self) -> RequestDispatcher:
        if self._rd is None:
            keys_view = ClassDispatcherKeysView({PipelineEvalMixin})
            for elem in self.elements:
                keys_view = keys_view.intersect(elem.get_request_dispatcher().keys())
            self._rd = keys_view.bind('_proxy_provide')

        return self._rd

    def _proxy_provide(self, factory: Mediator, request: Request):
        if not isinstance(request, PipelineEvalMixin):
            raise CannotProvide

        return request.eval_pipeline(  # type: ignore
            list(self.elements), factory, request
        )

    def __or__(self, other: Provider):
        if isinstance(other, Pipeline):
            return Pipeline(self.elements + other.elements)
        return Pipeline(self.elements + (other,))
