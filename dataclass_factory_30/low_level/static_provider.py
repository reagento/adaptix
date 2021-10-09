from inspect import isfunction
from typing import ClassVar, Type, TypeVar, Callable, Dict

from ..core import Provider, RequestDispatcher, Request, SearchState, BaseFactory
from ..type_tools import is_subclass_soft

RequestTV = TypeVar('RequestTV', bound=Request)
ProviderTV = TypeVar('ProviderTV', bound=Provider)
SearchStateTV = TypeVar('SearchStateTV', bound=SearchState)
T = TypeVar('T')


def static_provision_action(request_cls: Type[RequestTV]):
    if not is_subclass_soft(request_cls, Request):
        if isfunction(request_cls) or hasattr(request_cls, '__func__'):
            seems = " It seems you apply decorator without argument"
        else:
            seems = ""

        raise TypeError(
            "The argument of @static_provision_action must be a subclass of Request." + seems
        )

    def decorator(func: Callable[[ProviderTV, BaseFactory, SearchState, RequestTV], T]):
        func._spa_request_cls = request_cls  # type: ignore
        return func

    return decorator


class StaticProvider(Provider):
    """Provider whose RequestDispatcher is the same among all instances.

    Subclass defines provision actions wrapping method by decorator
    @static_provision_action(request_cls). Argument of decorator attaching
    method to specified Request class.
    It means that that provision action will be called for specified
    request or it's subclass. See :class Provider: for details.

    Subclasses cannot have multiple methods attached to the same request

    During subclassing StaticProvider goes through attributes of class
    and collects all methods wrapped by @static_provision_action() decorator
    to create the RequestDispatcher
    """
    _sp_cls_request_dispatcher: ClassVar[RequestDispatcher] = RequestDispatcher()

    def get_request_dispatcher(self) -> RequestDispatcher:
        return self._sp_cls_request_dispatcher

    def __init_subclass__(cls, **kwargs):
        mapping: Dict[Type[Request], str] = {}

        for attr_name in dir(cls):
            try:
                attr_value = getattr(cls, attr_name)
            except AttributeError:
                continue
            if hasattr(attr_value, '_spa_request_cls'):
                rc = attr_value._spa_request_cls
                if rc in mapping:
                    old_name = mapping[rc]
                    raise TypeError(
                        f"The {cls} has several @static_provision_action"
                        " that attached to the same Request class"
                        f" ({attr_name!r} and {old_name!r} attached to {rc})"
                    )

                mapping[rc] = attr_name

        cls._sp_cls_request_dispatcher = RequestDispatcher(mapping)
