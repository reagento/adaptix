import inspect
from inspect import isfunction
from typing import ClassVar, Type, TypeVar, Callable, Dict, Iterable, overload

from .class_dispatcher import ClassDispatcher
from .essential import Provider, Request, Mediator, CannotProvide
from ..type_tools import is_subclass_soft, normalize_type, strip_tags

__all__ = ('StaticProvider', 'static_provision_action', 'RequestDispatcher')

RequestDispatcher = ClassDispatcher[Request, str]

R = TypeVar('R', bound=Request)
P = TypeVar('P', bound=Provider)
T = TypeVar('T')
SPA = Callable[[P, Mediator, R], T]

_SPA_RC_STORAGE = '_spa_request_cls'


@overload
def static_provision_action() -> Callable[[SPA[P, R, T]], SPA[P, R, T]]:
    pass


@overload
def static_provision_action(__request_cls: Type[Request]) -> Callable[[SPA[P, R, T]], SPA[P, R, T]]:
    pass


@overload
def static_provision_action(__func: SPA[P, R, T]) -> SPA[P, R, T]:
    pass


def static_provision_action(__arg=None):
    """Marks method as @static_provision_action
    See :class StaticProvider: for details
    """

    if __arg is None:
        return static_provision_action

    if is_subclass_soft(__arg, Request):
        return _make_spa_decorator(__arg)

    if isfunction(__arg):
        return _make_spa_decorator(_infer_rc(__arg))(__arg)

    if hasattr(__arg, '__func__'):
        return _make_spa_decorator(_infer_rc(__arg.__func__))(__arg)

    raise TypeError(
        "static_provision_action must be applied"
        " as @static_provision_action or @static_provision_action()"
        " or @static_provision_action(Request)"
    )


def _infer_rc(func) -> Type[Request]:
    signature = inspect.signature(func)

    params = list(signature.parameters.values())

    if len(params) != 3:
        raise ValueError("Can not infer request class from callable")

    if params[2].annotation == signature.empty:
        raise ValueError("Can not infer request class from callable")

    request_tp = strip_tags(normalize_type(params[2].annotation))

    if is_subclass_soft(request_tp.origin, Request):
        return params[2].annotation

    raise TypeError("Request parameter must be subclass of Request")


def _make_spa_decorator(request_cls: Type[R]):
    def spa_decorator(func: Callable[[P, Mediator, R], T]):
        if hasattr(func, _SPA_RC_STORAGE):
            raise ValueError(
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

    You can omit request_cls parameter and decorator try to infer it introspecting method signature.

    Subclasses cannot have multiple methods attached to the same request.

    During subclassing, StaticProvider goes through attributes of the class
    and collects all methods wrapped by @static_provision_action() decorator.
    Then it merges new @static_provision_action's with the parent ones
    and creates the RequestDispatcher.
    """
    _sp_cls_request_dispatcher: ClassVar[RequestDispatcher] = RequestDispatcher()

    def __init_subclass__(cls, **kwargs):
        own_spa = _collect_class_own_rc_dict(cls)

        parent_rd_dicts = [
            parent._sp_cls_request_dispatcher.to_dict()
            for parent in cls.__bases__
            if issubclass(parent, StaticProvider)
        ]

        result = _merge_rc_dicts(cls, parent_rd_dicts + [own_spa])

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


_RcDict = Dict[Type[Request], str]


def _collect_class_own_rc_dict(cls) -> _RcDict:
    mapping: _RcDict = {}

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


def _merge_rc_dicts(cls: type, dict_iter: Iterable[_RcDict]) -> _RcDict:
    name_to_rc: Dict[str, Type[Request]] = {}
    rc_to_name: _RcDict = {}
    for dct in dict_iter:
        for rc, name in dct.items():
            if rc in rc_to_name.keys():
                raise _rc_attached_to_several_spa(cls, rc_to_name[rc], name, rc)

            if name in name_to_rc.keys() and rc != name_to_rc[name]:
                raise _spa_has_different_rc(cls, name, name_to_rc[name], rc)

            rc_to_name[rc] = name
            name_to_rc[name] = rc

    return rc_to_name
