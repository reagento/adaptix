import builtins
from typing import Any, Dict, Optional

_BUILTINS_DICT = {
    getattr(builtins, name): (getattr(builtins, name), name)
    for name in sorted(dir(builtins))
    if not name.startswith('__')
}


def get_literal_expr(obj: object) -> Optional[str]:
    if type(obj) in (int, float, str, bytes, bytearray):
        return repr(obj)

    try:
        b_obj, name = _BUILTINS_DICT[obj]
    except (KeyError, TypeError):
        try:
            return _get_complex_literal_expr(obj)
        except ValueError:
            return None

    if obj is b_obj:
        return name
    return None


def _provide_lit_expr(obj: object) -> str:
    literal_repr = get_literal_expr(obj)
    if literal_repr is None:
        raise ValueError
    return literal_repr


def _parenthesize(parentheses: str, elements) -> str:
    return parentheses[0] + ", ".join(map(_provide_lit_expr, elements)) + parentheses[1]


def _get_complex_literal_expr(obj: object) -> Optional[str]:
    # pylint: disable=unidiomatic-typecheck,too-many-return-statements
    if type(obj) == list:
        return _parenthesize("[]", obj)

    if type(obj) == tuple:
        return _parenthesize("()", obj)

    if type(obj) == set:
        if obj:
            return _parenthesize("{}", obj)
        return "set()"

    if type(obj) == frozenset:
        if obj:
            return "frozenset(" + _parenthesize("{}", obj) + ")"
        return "frozenset()"

    if type(obj) == slice:
        parts = (obj.start, obj.step, obj.stop)  # type: ignore[attr-defined]
        return "slice" + _parenthesize("()", parts)

    if type(obj) == range:
        parts = (obj.start, obj.step, obj.stop)  # type: ignore[attr-defined]
        return "range" + _parenthesize("()", parts)

    if type(obj) == dict:
        body = ", ".join(
            f"{_provide_lit_expr(key)}: {_provide_lit_expr(value)}"
            for key, value in obj.items()  # type: ignore[attr-defined]
        )
        return "{" + body + "}"

    return None


_CLS_TO_FACTORY_LITERAL: Dict[Any, str] = {
    list: '[]',
    dict: '{}',
    tuple: '()',
    str: '""',
    bytes: 'b""',
}


def get_literal_from_factory(obj: object) -> Optional[str]:
    try:
        return _CLS_TO_FACTORY_LITERAL.get(obj, None)
    except TypeError:
        return None
