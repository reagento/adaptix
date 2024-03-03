from importlib import import_module
from typing import Any, Callable


def load_by_object_ref(object_ref: str) -> Any:
    modname, qualname_sep, qualname = object_ref.partition(":")
    obj = import_module(modname)
    if qualname_sep:
        for attr in qualname.split("."):
            obj = getattr(obj, attr)
    return obj


def get_function_object_ref(func: Callable) -> str:
    return f"{func.__module__}:{func.__qualname__}"
