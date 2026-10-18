import dataclasses
import gc
import re
import sys
from collections.abc import Iterable
from dataclasses import is_dataclass
from textwrap import dedent
from traceback import format_exception
from typing import Any, Callable, Mapping, Optional, TypeVar, Union

import pytest

from adaptix import CannotProvide, ProviderNotFoundError
from adaptix._internal.compat import CompatExceptionGroup
from adaptix._internal.struct_trail import get_trail
from adaptix._internal.type_tools import is_parametrized

E = TypeVar("E", bound=Exception)


def reference_counts(values: Iterable[Any]) -> list[int]:
    # On Python 3.10, tracing can keep deleted locals and their tracebacks alive
    # until the caller's locals dictionary is synchronized with its fast locals.
    frame_locals = sys._getframe(1).f_locals
    del frame_locals
    gc.collect()
    return [sys.getrefcount(value) for value in values]


def _repr_value(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, Exception):
        return obj

    result = {}
    if is_dataclass(obj):
        result.update(
            **{
                fld.name: _repr_value(getattr(obj, fld.name))
                for fld in dataclasses.fields(obj)
            },
        )
    if isinstance(obj, CompatExceptionGroup):
        result["message"] = obj.message
        result["exceptions"] = [_repr_value(exc) for exc in obj.exceptions]
    if isinstance(obj, CannotProvide):
        result["message"] = obj.message
        result["is_terminal"] = obj.is_terminal
        result["is_demonstrative"] = obj.is_demonstrative
    if isinstance(obj, ProviderNotFoundError):
        result["message"] = obj.message
        result["description"] = obj.description
    if not result:
        result["args"] = [_repr_value(arg) for arg in obj.args]
    return {
        "__type__": type(obj),
        "__trail__": list(get_trail(obj)),
        **result,
        "__cause__": _repr_value(obj.__cause__),
        "__notes__": getattr(obj, "__notes__", []),
    }


def raises_exc(
    exc: Union[type[E], E],
    func: Callable[[], Any],
    *,
    match: Optional[str] = None,
) -> E:
    exc_type = exc if isinstance(exc, type) else type(exc)

    with pytest.raises(exc_type, match=match) as exc_info:
        func()

    assert _repr_value(exc_info.value) == _repr_value(exc)

    return exc_info.value


def _prepare_reference(reference: str, replaces: Mapping[str, Any]) -> str:
    text_replaces = {
        src: format(target) for src, target in replaces.items()
    }
    pattern = re.compile(
        "|".join(
            map(re.escape, sorted(text_replaces.keys(), key=len, reverse=True)),
        ),
    )
    return pattern.sub(
        lambda match: text_replaces[match.group()],
        dedent(reference).lstrip(),
    )


def raises_exc_text(
    func: Callable[[], Any],
    reference: str,
    replaces: Optional[Mapping[str, Any]] = None,
) -> None:
    try:
        func()
    except Exception as e:
        e.__traceback__ = None
        current = "".join(format_exception(type(e), e, e.__traceback__))
        final_reference = _prepare_reference(reference, replaces or {})
        assert current == final_reference
    else:
        raise AssertionError("Error is not raised")


def parametrize_bool(param: str, *params: str):
    full_params = [param, *params]

    def decorator(func):
        for p in full_params:
            func = pytest.mark.parametrize(
                p, [False, True],
                ids=[f"{p}=False", f"{p}=True"],
            )(func)
        return func

    return decorator


def cond_list(flag: object, lst: Union[Callable[[], list], list]) -> list:
    if flag:
        return lst() if callable(lst) else lst
    return []


def full_match(string_to_match: str) -> str:
    return "^" + re.escape(string_to_match) + "$"


def pretty_typehint_test_id(config, val, argname):
    if is_parametrized(val):
        return str(val)
    try:
        return val.__name__
    except AttributeError:
        try:
            return val._name
        except AttributeError:
            return None
