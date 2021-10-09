from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from typing import Type, TypeVar, Generic, final, Optional, List, Tuple, Sequence

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


class SearchState(ABC):
    @abstractmethod
    def start_from_next(self: T) -> T:
        """Start search from subsequent item of full recipe"""
        raise NotImplementedError


V = TypeVar('V')
ProviderTV = TypeVar('ProviderTV', bound='Provider')
SearchStateTV = TypeVar('SearchStateTV', bound=SearchState)


def _make_pipeline(left, right) -> 'Pipeline':
    if isinstance(left, Pipeline):
        left_elems = left.elements
    else:
        left_elems = (left,)

    if isinstance(right, Pipeline):
        right_elems = right.elements
    else:
        right_elems = (right,)

    return Pipeline(
        left_elems + right_elems
    )


class PipeliningMixin:
    """A mixin that makes your class able to create a pipeline"""

    @final
    def __or__(self, other) -> 'Pipeline':
        return _make_pipeline(self, other)

    @final
    def __ror__(self, other) -> 'Pipeline':
        return _make_pipeline(other, self)


RequestDispatcher = ClassDispatcher[Request, str]


class Provider(PipeliningMixin):
    """A provider is an object that can process Request instances.
    It defines methods called provision action
    that takes 3 arguments (BaseFactory, SearchState, Request)
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
    def apply_provider(self, factory: 'BaseFactory', s_state: SearchStateTV, request: Request[T]) -> T:
        """This method is suitable wrapper
        around :method get_request_dispatcher: and getattr().
        Factory may not use this method
        implementing own cached provision action call.
        """
        try:
            attr_name = self.get_request_dispatcher().dispatch(type(request))
        except KeyError:
            raise CannotProvide

        return getattr(self, attr_name)(factory, s_state, request)


class NoSuitableProvider(ValueError):
    pass


class BaseFactory(ABC, Generic[SearchStateTV]):
    """Factory responds to requests object using a recipe.

    The recipe is a list that consists of :class:`Provider` or objects
    that a factory could cast to Provider via :method:`ensure_provider`.

    When you call :method:`provide`, a factory look for a suitable provider in a full recipe.
    The Full recipe is a sum of instance recipe and class recipe in MRO.
    See :method:`provide` for details of this process.

    :method:`provide` is a low-level method. Subclasses should introduce own user-friendly methods
    like `.parser()` of :class:`ParserFactory` or `.json_schema()` of :class:`JsonSchemaFactory`
    """
    recipe: list

    @abstractmethod
    def ensure_provider(self, value) -> Provider:
        """Create :class:`Provider` instance from value
        This method have to be used by :method:`provide` to convert each item of full recipe
        to provider.

        :raise ValueError: Con not create Provider from given object
        """
        raise NotImplementedError

    @abstractmethod
    def create_init_search_state(self) -> SearchStateTV:
        raise NotImplementedError

    @abstractmethod
    def provide_with(self, s_state: SearchStateTV, request: Request[T]) -> T:
        """Get response of sent request.

        :param s_state: Search State of Factory.
        If the factory should start the search from begging,
        pass a result of :method:`create_init_search_state`

        :param request: A request instance
        :return: Result of the request processing
        :raise NoSuitableProvider: A provider able to process the request does not found
        """
        raise NotImplementedError

    @final
    def provide(self, request: Request[T]) -> T:
        """Get a response to the sent request.
        Search starts from the beginning of the factory recipe.
        This method is wrapper around
        :method:`provide_with` and :method:`create_init_search_state`

        :param request: A request instance
        :return: Result of the request processing
        :raise NoSuitableProvider: A provider able to process the request does not found
        """
        return self.provide_with(self.create_init_search_state(), request)


def _get_class_own_recipe(cls: type) -> list:
    if (
        issubclass(cls, BaseFactory)
        and 'recipe' in vars(cls)
        and isinstance(cls.recipe, list)
    ):
        return cls.recipe
    return []


def collect_class_full_recipe(factory_cls: Type[BaseFactory]) -> list:
    """Creates full recipe by concatenating all recipe attributes
    of classes in mro until BaseFactory.
    If recipe attribute is not a list (e.g. dataclasses.Field) it will be ignored
    """
    result = []
    for item in factory_cls.mro():
        result.extend(
            _get_class_own_recipe(item)
        )
    return result


class PipelineEvalMixin(ABC):
    """A special mixin for Request that allows to eval pipeline.
    Subclass should implement :method:`eval_pipeline`
    """

    @classmethod
    @abstractmethod
    def eval_pipeline(
        cls,
        providers: List[Provider],
        factory: BaseFactory,
        s_state: SearchState,
        request: Request
    ):
        pass


class Pipeline(Provider, PipeliningMixin, Generic[V]):
    def __init__(self, elements: Tuple[V, ...]):
        self.elements = elements
        self._rd: Optional[RequestDispatcher] = None

    def get_request_dispatcher(self) -> RequestDispatcher:
        if self._rd is None:
            keys_view = ClassDispatcherKeysView({Request})
            for elem in self.elements:
                if isinstance(elem, Provider):
                    keys_view = keys_view.intersect(elem.get_request_dispatcher().keys())
            self._rd = keys_view.bind('_proxy_provide')

        return self._rd

    def _proxy_provide(self, factory: BaseFactory, s_state: SearchState, request: Request):
        if not isinstance(request, PipelineEvalMixin):
            raise CannotProvide

        providers = [factory.ensure_provider(el) for el in self.elements]

        return request.eval_pipeline(  # type: ignore
            providers, factory, s_state, request
        )
