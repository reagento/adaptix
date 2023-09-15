import logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Reversible, Sequence, TypeVar, Union

from adaptix._internal.feature_requirement import HAS_NATIVE_EXC_GROUP


class TrailElementMarker:
    pass


@dataclass(frozen=True)
class Attr(TrailElementMarker):
    name: str

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r})"


@dataclass(frozen=True)
class ItemKey(TrailElementMarker):
    key: Any

    def __repr__(self):
        return f"{type(self).__name__}({self.key!r})"


# TrailElement describes how to extract next object from the source.
# By default, you must subscribe source to get next object,
# except with TrailElementMarker children that define custom way to extract values.
# For example, Attr means that next value must be gotten by attribute access
TrailElement = Union[str, int, Any, TrailElementMarker]
Trail = Sequence[TrailElement]

T = TypeVar('T')


def append_trail(obj: T, trail_element: TrailElement) -> T:
    """Append a trail element to object. Trail stores in special attribute,
    if an object does not allow adding 3rd-party attributes, do nothing.
    Element inserting to start of the path (it is built in reverse order)
    """
    # pylint: disable=protected-access
    try:
        # noinspection PyProtectedMember
        trail = obj._adaptix_struct_trail  # type: ignore[attr-defined]
    except AttributeError:
        obj._adaptix_struct_trail = deque([trail_element])  # type: ignore[attr-defined]
    else:
        trail.appendleft(trail_element)
    return obj


def extend_trail(obj: T, sub_trail: Reversible[TrailElement]) -> T:
    """Extend a trail with a sub trail. Trail stores in special attribute,
    if an object does not allow adding 3rd-party attributes, do nothing.
    Sub path inserting to start of the path (it is built in reverse order)
    """
    # pylint: disable=protected-access
    try:
        # noinspection PyProtectedMember
        trail = obj._adaptix_struct_trail  # type: ignore[attr-defined]
    except AttributeError:
        obj._adaptix_struct_trail = deque(sub_trail)  # type: ignore[attr-defined]
    else:
        trail.extendleft(reversed(sub_trail))
    return obj


def get_trail(obj: object) -> Trail:
    """Retrieve path from object. Trail stores in special private attribute that never be accessed directly"""
    try:
        # noinspection PyProtectedMember
        return obj._adaptix_struct_trail  # type: ignore[attr-defined]  # pylint: disable=protected-access
    except AttributeError:
        return deque()


BaseExcT = TypeVar('BaseExcT', bound=BaseException)

if HAS_NATIVE_EXC_GROUP:
    def render_trail_as_note(exc: BaseExcT) -> BaseExcT:
        exc.add_note(f'Exception was caused at {list(get_trail(exc))}')
        return exc
else:
    def render_trail_as_note(exc: BaseExcT) -> BaseExcT:
        if hasattr(exc, '__notes__'):
            exc.__notes__.append(f'Exception was caused at {list(get_trail(exc))}')
        else:
            exc.__notes__ = [f'Exception was caused at {list(get_trail(exc))}']
        return exc


# TODO: remove this
class PathedException(Exception):
    def __init__(self, exc: Exception, path: Trail):
        self.exc = exc
        self.path = path

    def __str__(self):
        exc_instance_desc = f': {self.exc}' if str(self.exc) else ''
        return f'at {list(self.path)} was raised {type(self.exc).__qualname__}{exc_instance_desc}'


# TODO: remove this
class ExcPathRenderer:
    """Special context manager that wraps unhandled exception with :class:`PathedException`.
    This allows to render struct_path at console. Object should be used debug purposes only.

    Example::

         with ExcPathRenderer():
             print(retort.load(some_data, SomeModel))
    """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return

        exc_path = get_trail(exc_val)
        raise PathedException(exc_val, exc_path)


# TODO: remove this
def default_trail_processor(path):
    return [
        element if isinstance(element, (int, str)) else repr(element)
        for element in path
    ]


# TODO: remove this
class StructPathRendererFilter(logging.Filter):
    __slots__ = ('_attr_name', '_path_processor')

    def __init__(
        self,
        attr_name: str = 'struct_path',
        path_processor: Callable[[Trail], Any] = default_trail_processor,
    ):
        super().__init__()
        self._attr_name = attr_name
        self._path_processor = path_processor

    def filter(self, record: logging.LogRecord) -> bool:
        """Modify record adding information about exception path"""
        if record.exc_info is not None:
            setattr(
                record,
                self._attr_name,
                self._path_processor(get_trail(record.exc_info[1])),
            )
        return True
