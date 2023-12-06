import inspect
from inspect import isfunction
from typing import Callable, ClassVar, Dict, Iterable, Type, TypeVar, final, overload

from ..datastructures import ClassDispatcher
from ..type_tools import get_all_type_hints, is_subclass_soft, normalize_type, strip_tags
from .essential import CannotProvide, Mediator, Provider, Request
from .provider_wrapper import RequestClassDeterminedProvider

__all__ = ('StaticProvider', 'static_provision_action', 'RequestDispatcher')

RequestDispatcher = ClassDispatcher[Request, str]

R = TypeVar('R', bound=Request)
P = TypeVar('P', bound=Provider)
T = TypeVar('T')
SPA = Callable[[P, Mediator[T], R], T]

_SPA_RC_STORAGE = '_spa_request_cls'


@overload
def static_provision_action() -> Callable[[SPA[P, T, R]], SPA[P, T, R]]:
    ...


@overload  # type: ignore[overload-overlap]
def static_provision_action(request_cls: Type[Request], /) -> Callable[[SPA[P, T, R]], SPA[P, T, R]]:
    ...


@overload
def static_provision_action(func: SPA[P, T, R], /) -> SPA[P, T, R]:
    ...


def static_provision_action(arg=None):
    """Marks method as ``@static_provision_action``.
    See :class:`StaticProvider` for details
    """

    if arg is None:
        return static_provision_action

    if is_subclass_soft(arg, Request):
        return _make_spa_decorator(arg)

    if isfunction(arg):
        return _make_spa_decorator(_infer_rc(arg))(arg)

    if hasattr(arg, '__func__'):
        return _make_spa_decorator(_infer_rc(arg.__func__))(arg)

    raise TypeError(
        "static_provision_action must be applied"
        " as @static_provision_action or @static_provision_action()"
        " or @static_provision_action(Request)"
    )


def _infer_rc(func) -> Type[Request]:
    signature = inspect.signature(func)

    params = list(signature.parameters.values())

    if len(params) < 3:
        raise ValueError("Can not infer request class from callable")

    if params[2].annotation == signature.empty:
        raise ValueError("Can not infer request class from callable")

    type_hints = get_all_type_hints(func)
    request_tp = strip_tags(normalize_type(type_hints[params[2].name]))

    if is_subclass_soft(request_tp.origin, Request):
        return request_tp.source

    raise TypeError("Request parameter must be subclass of Request")


def _make_spa_decorator(request_cls: Type[R]):
    def spa_decorator(func: Callable[[P, Mediator, R], T]):
        if hasattr(func, _SPA_RC_STORAGE):
            raise ValueError("@static_provision_action decorator cannot be applied twice")

        setattr(func, _SPA_RC_STORAGE, request_cls)
        return func

    return spa_decorator


class StaticProvider(RequestClassDeterminedProvider):
    """Provider which instances can process same set of Request classes.

    Subclass defines provision actions wrapping method by decorator
    ``@static_provision_action(request_cls)``. Argument of decorator attaching
    method to specified Request class.
    It means that that provision action will be called for specified
    request, or it's subclass. See :class:`Provider` for details.

    You can omit request_cls parameter and decorator try to infer it introspecting method signature.

    Subclasses cannot have multiple methods attached to the same request.

    During subclassing, ``StaticProvider`` goes through attributes of the class
    and collects all methods wrapped by :func:`static_provision_action` decorator.
    Then it merges list of new :func:`static_provision_action`'s with the parent ones.
    """
    _sp_cls_request_dispatcher: ClassVar[RequestDispatcher] = RequestDispatcher()

    def __init_subclass__(cls, **kwargs):
        own_spa = _collect_class_own_rc_dict(cls)

        parent_rd_dicts = [
            parent._sp_cls_request_dispatcher.to_dict()  # pylint: disable=no-member
            for parent in cls.__bases__
            if issubclass(parent, StaticProvider)
        ]

        result = _merge_rc_dicts(cls, parent_rd_dicts + [own_spa])

        cls._sp_cls_request_dispatcher = RequestDispatcher(result)

    @final
    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        try:
            attr_name = self._sp_cls_request_dispatcher.dispatch(type(request))
        except KeyError:
            raise CannotProvide

        return getattr(self, attr_name)(mediator, request)

    @final
    def maybe_can_process_request_cls(self, request_cls: Type[Request]) -> bool:
        try:
            self._sp_cls_request_dispatcher.dispatch(request_cls)
        except KeyError:
            return False
        return True


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
            if rc in rc_to_name:
                raise _rc_attached_to_several_spa(cls, rc_to_name[rc], name, rc)

            if name in name_to_rc and rc != name_to_rc[name]:
                raise _spa_has_different_rc(cls, name, name_to_rc[name], rc)

            rc_to_name[rc] = name
            name_to_rc[name] = rc

    return rc_to_name
