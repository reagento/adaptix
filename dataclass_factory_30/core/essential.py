from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from inspect import isfunction
from typing import Type, TypeVar, Generic, final, Optional, Callable, ClassVar, List, Tuple, Sequence, Set

from .class_dispatcher import ClassDispatcher
from ..type_tools import is_subclass_soft

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


V = TypeVar('V')
ProviderTV = TypeVar('ProviderTV', bound='Provider')
RequestTV = TypeVar('RequestTV', bound=Request)
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


def provision_action(request_cls: Type[RequestTV]):
    """Marks method as provision_action and attaches specified request class

    See :class:`Provider` for details.
    """

    if not is_subclass_soft(request_cls, Request):
        if isfunction(request_cls):
            seems = " It seems you apply decorator without argument"
        else:
            seems = ""

        raise TypeError(
            "The argument of @provision_action must be a subclass of Request." + seems
        )

    def decorator(func: Callable[[ProviderTV, 'BaseFactory', SearchState, RequestTV], T]):
        func._pa_request_cls = request_cls  # type: ignore
        return func

    return decorator


RequestDispatcher = ClassDispatcher[Request, str]


def _collect_class_own_rd(cls: Type['Provider']) -> RequestDispatcher:
    # noinspection PyProtectedMember
    rd_dict = {
        attr_value._pa_request_cls: name
        for name, attr_value in vars(cls).items()
        if isfunction(attr_value) and hasattr(attr_value, '_pa_request_cls')
    }

    return ClassDispatcher(rd_dict)


class Provider(PipeliningMixin):
    """The provider is a central part of the core API.

    Providers can define special methods that can process Request instances.
    They are called provision action
    and could be created by the @provision_action decorator.
    You have to attach the Request class to every provision action.
    The factory will select provision action
    which Request type will be a supertype of actual request
    and will be the closest in MRO to actual.

    You can not define several provision actions
    that are attached to one request class.

    The child class inherits all provision action.
    You can delete inherited provision action
    by setting such attribute to None.

    Each provision action takes BaseFactory,
    SearchState, and instance of attached Request subclass.
    SearchState is created by Factory.

    Subclasses must call __init__ of Provider.
    Be careful with dataclasses.
    It requires a to call parent __init__ inside __post_init__.
    You can pass an instance of ClassDispatcher
    that will merge with class dispatching.
    This is very useful for decorators, wrapper and etc.

    Any provision action must return value
    of expected type otherwise raise :exception:`CannotProvide`.
    """
    _cls_request_dispatcher: ClassVar[RequestDispatcher] = ClassDispatcher()

    def __init_subclass__(cls, **kwargs):
        none_attrs: Set[str] = {
            name for name, attr_value in vars(cls).items()
            if attr_value is None
        }

        parent_dispatch: RequestDispatcher = ClassDispatcher()
        for base in reversed(cls.__bases__):
            if issubclass(base, Provider):
                parent_dispatch = parent_dispatch.merge(
                    base._cls_request_dispatcher.remove_values(none_attrs),
                )

        cls._cls_request_dispatcher = parent_dispatch.merge(
            _collect_class_own_rd(cls)
        )

    def __init__(self, request_dispatcher: Optional[RequestDispatcher] = None):
        if request_dispatcher is None:
            self._provider_request_dispatcher = self._cls_request_dispatcher
        else:
            self._provider_request_dispatcher = self._cls_request_dispatcher.merge(
                request_dispatcher
            )

    @property
    def request_dispatcher(self) -> RequestDispatcher:
        return self._provider_request_dispatcher

    @final
    def apply_provider(self, factory: 'BaseFactory', s_state: SearchStateTV, request: Request[T]) -> T:
        """This method is suitable wrapper
        around request_dispatcher property and getattr.
        Factory may not use this method
        implementing own cached provision action call.
        """
        try:
            attr_name = self.request_dispatcher[type(request)]
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
    def provide(self, s_state: SearchStateTV, request: Request[T]) -> T:
        """Get response of sent request.

        :param s_state: Search State of Factory.
                        If factory should start search from begging,
                        pass a result of :method:`create_init_search_state`
        :param request:
        :return: A result of request processing
        :raise NoSuitableProvider: A provider that can process request does not found
        """
        raise NotImplementedError


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


@dataclass(frozen=True)
class Pipeline(Provider, PipeliningMixin, Generic[V]):
    elements: Tuple[V, ...]

    def __post_init__(self):
        super().__init__()

    @provision_action(Request)
    def _proxy_provide(self, factory: BaseFactory, s_state: SearchState, request: Request):
        if not issubclass(type(request), PipelineEvalMixin):
            raise CannotProvide

        providers = [factory.ensure_provider(el) for el in self.elements]

        return request.eval_pipeline(  # type: ignore
            providers, factory, s_state, request
        )
