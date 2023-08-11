from functools import wraps
from typing import Any, Callable, Optional, overload

from adaptix._internal.utils import get_prefix_groups


class MangledConstant:
    def __init__(self, value: str):
        self._value = value

    @property
    def value(self):
        return self._value

    @overload
    def __get__(self, instance: None, owner) -> 'MangledConstant':
        pass

    @overload
    def __get__(self, instance: Any, owner) -> str:
        pass

    def __get__(self, instance, owner):
        if instance is None:
            return self

        return self._value

    def __set__(self, instance, value):
        raise AttributeError("Can not rewrite MangledConstant at instance")


def mangling_method(prefix: str):
    def decorator(func: Callable[..., str]) -> Callable[..., str]:
        @wraps(func)
        def wrapped_method(self, *args, **kwargs):
            return prefix + func(self, *args, **kwargs)

        # pylint: disable=protected-access
        wrapped_method._mangling_method_prefix = prefix  # type: ignore[attr-defined]
        return wrapped_method

    return decorator


def _get_obj_prefix(obj: Any) -> Optional[str]:
    if isinstance(obj, MangledConstant):
        return obj.value
    return getattr(obj, '_mangling_method_prefix', None)


class PrefixManglerBase:
    def __init_subclass__(cls, **kwargs):
        prefixes = [
            prefix for prefix in (
                _get_obj_prefix(getattr(cls, attr))
                for attr in dir(cls)
            )
            if prefix is not None
        ]
        prefix_groups = get_prefix_groups(prefixes)
        if prefix_groups:
            raise ValueError(f"Prefix overlapping {prefix_groups}")
        cls._prefixes = prefixes
