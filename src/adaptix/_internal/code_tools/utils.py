import builtins
import math
from enum import Enum
from typing import Any, Dict, Optional

BUILTIN_TO_NAME = {
    getattr(builtins, name): name
    for name in sorted(dir(builtins))
    if not name.startswith('__') and name != '_'
}
NAME_TO_BUILTIN = {name: obj for obj, name in BUILTIN_TO_NAME.items()}


class _CannotBeRendered(Exception):
    pass


def get_literal_expr(obj: object) -> Optional[str]:
    # pylint: disable=unidiomatic-typecheck,too-many-return-statements
    if type(obj) in (int, str, bytes, bytearray):
        return repr(obj)
    if type(obj) is float:
        if math.isinf(obj) or math.isnan(obj):
            return None
        return repr(obj)

    try:
        name = BUILTIN_TO_NAME[obj]
    except (KeyError, TypeError):
        try:
            return _get_complex_literal_expr(obj)
        except _CannotBeRendered:
            return None

    return name


def _provide_lit_expr(obj: object) -> str:
    literal_repr = get_literal_expr(obj)
    if literal_repr is None:
        raise _CannotBeRendered
    return literal_repr


def _parenthesize(parentheses: str, elements) -> str:
    return parentheses[0] + ", ".join(map(_provide_lit_expr, elements)) + parentheses[1]


def _try_sort(iterable):
    try:
        return sorted(iterable)
    except TypeError:
        return iterable


def _get_complex_literal_expr(obj: object) -> Optional[str]:
    # pylint: disable=unidiomatic-typecheck,too-many-return-statements
    if type(obj) is list:
        return _parenthesize("[]", obj)

    if type(obj) is tuple:
        return _parenthesize("()", obj)

    if type(obj) is set:
        if obj:
            return _parenthesize("{}", _try_sort(obj))
        return "set()"

    if type(obj) is frozenset:
        if obj:
            return "frozenset(" + _parenthesize("{}", _try_sort(obj)) + ")"
        return "frozenset()"

    if type(obj) is slice:
        parts = (obj.start, obj.step, obj.stop)
        return "slice" + _parenthesize("()", parts)

    if type(obj) is range:
        parts = (obj.start, obj.step, obj.stop)
        return "range" + _parenthesize("()", parts)

    if type(obj) is dict:
        body = ", ".join(
            f"{_provide_lit_expr(key)}: {_provide_lit_expr(value)}"
            for key, value in obj.items()
        )
        return "{" + body + "}"

    return None


_CLS_TO_FACTORY_LITERAL: Dict[Any, str] = {
    list: '[]',
    dict: '{}',
    tuple: '()',
    str: '""',
    bytes: 'b""',
    type(None): 'None',
}


def get_literal_from_factory(obj: object) -> Optional[str]:
    try:
        return _CLS_TO_FACTORY_LITERAL.get(obj, None)
    except TypeError:
        return None


_SINGLETONS = {None, Ellipsis, NotImplemented}


def is_singleton(obj: object) -> bool:
    return obj in _SINGLETONS or isinstance(obj, (bool, Enum))
