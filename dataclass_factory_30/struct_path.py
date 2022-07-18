from collections import deque
from dataclasses import dataclass
from typing import Any, Optional, Reversible, Sequence, Union


class PathElementMarker:
    pass


@dataclass(frozen=True)
class Attr(PathElementMarker):
    name: str

    def __repr__(self):
        return f"{type(self)}({self.name!r})"


# PathElement describes how to extract next object from the source.
# By default, you must subscribe source to get next object,
# except with PathElementMarker children that define custom way to extract values.
# For example, Attr means that next value must be gotten by attribute access
PathElement = Union[str, int, Any, PathElementMarker]
Path = Sequence[PathElement]


def append_path(obj: object, path_element: PathElement) -> None:
    """Append path element to object. Path stores in special attribute,
    if object does not allow to add 3rd-party attributes, do nothing.
    Element inserting to start of the path (it is build in reverse order)
    """
    # pylint: disable=protected-access
    try:
        # noinspection PyProtectedMember
        path = obj._df_struct_path  # type: ignore[attr-defined]
    except AttributeError:
        try:
            obj._df_struct_path = deque([path_element])  # type: ignore[attr-defined]
        except AttributeError:
            pass
    else:
        path.appendleft(path_element)


def extend_path(obj: object, sub_path: Reversible[PathElement]) -> None:
    """Extend path with sub path. Path stores in special attribute,
    if object does not allow to add 3rd-party attributes, do nothing.
    Sub path inserting to start of the path (it is build in reverse order)
    """
    # pylint: disable=protected-access
    try:
        # noinspection PyProtectedMember
        path = obj._df_struct_path  # type: ignore[attr-defined]
    except AttributeError:
        try:
            obj._df_struct_path = deque(sub_path)  # type: ignore[attr-defined]
        except AttributeError:
            pass
    else:
        path.extendleft(reversed(sub_path))


def get_path(obj: object) -> Optional[Path]:
    """Retrieve path from object. Path stores in special attribute,
    if object does not allow to add 3rd-party attributes, returns None.

    Function needs to determine why object has no attribute -- it is does not support
    3rd-party attributes or path is empty.
    So it tests this trying to set value (!!!) for special attribute.
    If you do not want to mutate object use :function get_path_unchecked:
    """
    # pylint: disable=protected-access
    try:
        # noinspection PyProtectedMember
        path = obj._df_struct_path  # type: ignore[attr-defined]
    except AttributeError:
        try:
            obj._df_struct_path = deque()  # type: ignore[attr-defined]
        except AttributeError:
            return None
        return deque()
    return path


def get_path_unchecked(obj: object) -> Path:
    """Retrieve path from object. Path stores in special attribute,
    if object does not allow to add 3rd-party attributes, returns empty sequence.

    This function can not determine why object has no attribute -- it is does not support
    3rd-party attributes or path is empty, so it simply returns empty sequence.

    If you want to separate this two cases, use :function get_path:
    """
    try:
        # noinspection PyProtectedMember
        path = obj._df_struct_path  # type: ignore[attr-defined]  # pylint: disable=protected-access
    except AttributeError:
        return deque()
    return path
