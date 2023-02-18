import logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Reversible, Sequence, TypeVar, Union


class PathElementMarker:
    pass


@dataclass(frozen=True)
class Attr(PathElementMarker):
    name: str

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r})"


# PathElement describes how to extract next object from the source.
# By default, you must subscribe source to get next object,
# except with PathElementMarker children that define custom way to extract values.
# For example, Attr means that next value must be gotten by attribute access
PathElement = Union[str, int, Any, PathElementMarker]
Path = Sequence[PathElement]

T = TypeVar('T')


def append_path(obj: T, path_element: PathElement) -> T:
    """Append path element to object. Path stores in special attribute,
    if object does not allow to add 3rd-party attributes, do nothing.
    Element inserting to start of the path (it is build in reverse order)
    """
    # pylint: disable=protected-access
    try:
        # noinspection PyProtectedMember
        path = obj._adaptix_struct_path  # type: ignore[attr-defined]
    except AttributeError:
        obj._adaptix_struct_path = deque([path_element])  # type: ignore[attr-defined]
    else:
        path.appendleft(path_element)
    return obj


def extend_path(obj: T, sub_path: Reversible[PathElement]) -> T:
    """Extend path with sub path. Path stores in special attribute,
    if object does not allow to add 3rd-party attributes, do nothing.
    Sub path inserting to start of the path (it is build in reverse order)
    """
    # pylint: disable=protected-access
    try:
        # noinspection PyProtectedMember
        path = obj._adaptix_struct_path  # type: ignore[attr-defined]
    except AttributeError:
        obj._adaptix_struct_path = deque(sub_path)  # type: ignore[attr-defined]
    else:
        path.extendleft(reversed(sub_path))
    return obj


def get_path(obj: object) -> Path:
    """Retrieve path from object. Path stores in special private attribute that never be accessed directly"""
    try:
        # noinspection PyProtectedMember
        return obj._adaptix_struct_path  # type: ignore[attr-defined]  # pylint: disable=protected-access
    except AttributeError:
        return deque()


class PathedException(Exception):
    def __init__(self, exc: Exception, path: Path):
        self.exc = exc
        self.path = path

    def __str__(self):
        exc_instance_desc = f': {self.exc}' if str(self.exc) else ''
        return f'at {list(self.path)} was raised {type(self.exc).__qualname__}{exc_instance_desc}'


class PathExceptionRenderer:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return

        exc_path = get_path(exc_val)
        raise PathedException(exc_val, exc_path)


render_exc_path = PathExceptionRenderer()
# pylint: disable=attribute-defined-outside-init
render_exc_path.__doc__ = \
    """Special context manager that wraps unhandled exception with PathedException.
    This allows to render struct_path at console. Object should be used debug purposes only.

    Example::
         with render_exc_path:
            print(retort.load(some_data, SomeModel))
    """


def default_path_processor(path):
    return [
        element if isinstance(element, (int, str)) else str(element)
        for element in path
    ]


class StructPathRendererFilter(logging.Filter):
    __slots__ = ('_attr_name', '_path_processor')

    def __init__(
        self,
        attr_name: str = 'struct_path',
        path_processor: Callable[[Path], Any] = default_path_processor,
    ):
        super().__init__()
        self._attr_name = attr_name
        self._path_processor = path_processor

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info is not None:
            setattr(
                record,
                self._attr_name,
                self._path_processor(get_path(record.exc_info[1])),
            )
        return True
