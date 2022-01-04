from inspect import isfunction
from typing import ClassVar, Type, TypeVar, Callable, Dict, Iterable

from .class_dispatcher import ClassDispatcher
from .essential import Provider, Request, Mediator, CannotProvide
from ..type_tools import is_subclass_soft

RequestDispatcher = ClassDispatcher[Request, str]

RequestTV = TypeVar('RequestTV', bound=Request)
ProviderTV = TypeVar('ProviderTV', bound=Provider)
T = TypeVar('T')

_SPA_RC_STORAGE = '_spa_request_cls'


def static_provision_action(request_cls: Type[RequestTV]):
    """Marks method as @static_provision_action
    See :class StaticProvider: for details
    """

    if not is_subclass_soft(request_cls, Request):
        if isfunction(request_cls) or hasattr(request_cls, '__func__'):
            seems = " It seems you apply decorator without argument"
        else:
            seems = ""

        raise TypeError(
            "The argument of @static_provision_action must be a subclass of Request." + seems
        )

    def spa_decorator(func: Callable[[ProviderTV, Mediator, RequestTV], T]):
        if hasattr(func, _SPA_RC_STORAGE):
            raise TypeError(
                "@static_provision_action decorator cannot be applied twice"
            )

        setattr(func, _SPA_RC_STORAGE, request_cls)
        return func

    return spa_decorator


class StaticProvider(Provider):
    """Provider whose RequestDispatcher is the same among all instances.

    Subclass defines provision actions wrapping method by decorator
    @static_provision_action(request_cls). Argument of decorator attaching
    method to specified Request class.
    It means that that provision action will be called for specified
    request or it's subclass. See :class Provider: for details.

    Subclasses cannot have multiple methods attached to the same request

    During subclassing, StaticProvider goes through attributes of the class
    and collects all methods wrapped by @static_provision_action() decorator.
    Then it merges new @static_provision_action's with the parent ones
    and creates the RequestDispatcher
    """
    _sp_cls_request_dispatcher: ClassVar[RequestDispatcher] = RequestDispatcher()

    def __init_subclass__(cls, **kwargs):
        own_spa = _collect_class_own_rd_dict(cls)

        parent_rd_dicts = [
            parent._sp_cls_request_dispatcher.to_dict()
            for parent in cls.__bases__
            if issubclass(parent, StaticProvider)
        ]

        result = _merge_rd_dicts(cls, parent_rd_dicts + [own_spa])

        cls._sp_cls_request_dispatcher = RequestDispatcher(result)

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        try:
            attr_name = self._sp_cls_request_dispatcher.dispatch(type(request))
        except KeyError:
            raise CannotProvide

        return getattr(self, attr_name)(mediator, request)


def _rc_attached_to_several_spa(cls: type, name1: str, name2: str, rc: Type[Request]):
    return TypeError(
        f"The {cls} has several @static_provision_action"
        " that attached to the same Request class"
        f" ({name1!r} and {name2!r} attached to {rc})"
    )


def _spa_has_different_rc(cls: type, name: str, rc1: Type[Request], rc2: Type[Request]):
    return TypeError(
        f"The {cls} has @static_provision_action"
        " that attached to the different Request class"
        f" ({name!r} attached to {rc1} and {rc2})"
    )


_RdDict = Dict[Type[Request], str]


def _collect_class_own_rd_dict(cls) -> _RdDict:
    mapping: _RdDict = {}

    for attr_name in vars(cls):
        try:
            attr_value = getattr(cls, attr_name)
        except AttributeError:
            continue
        if hasattr(attr_value, _SPA_RC_STORAGE):
            rc = getattr(attr_value, _SPA_RC_STORAGE)
            if rc in mapping:
                old_name = mapping[rc]
                raise _rc_attached_to_several_spa(cls, attr_name, old_name, rc)

            mapping[rc] = attr_name

    return mapping


def _merge_rd_dicts(cls: type, dict_iter: Iterable[_RdDict]) -> _RdDict:
    name_to_rc: Dict[str, Type[Request]] = {}
    rc_to_name: _RdDict = {}
    for dct in dict_iter:
        for rc, name in dct.items():
            if rc in rc_to_name.keys():
                raise _rc_attached_to_several_spa(cls, rc_to_name[rc], name, rc)

            if name in name_to_rc.keys() and rc != name_to_rc[name]:
                raise _spa_has_different_rc(cls, name, name_to_rc[name], rc)

            rc_to_name[rc] = name
            name_to_rc[name] = rc

    return rc_to_name
