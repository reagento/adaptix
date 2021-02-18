from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, TYPE_CHECKING, Union


# https://github.com/python/typing/issues/684#issuecomment-548203158
if TYPE_CHECKING:
    ellipsis = ellipsis  # noqa F821
else:
    ellipsis = type(Ellipsis)

# normal value in field mapping
# str means key in dictionary
# int  means position in list
CleanKey = Union[str, int]
# sequence of kes means path in complete Dict/List structure
CleanPath = Tuple[CleanKey, ...]  # normal value

# same as CleanKey/CleanPath, but ellipsis allowed.
# all `...` are replaced for each field in every certain type with its name.
Key = Union[CleanKey, ellipsis]
Path = Tuple[Key, ...]
# real field name or `...` if this mapping can be applied to any field
FieldOrAuto = Union[str, ellipsis]

NameMapping = Optional[Dict[FieldOrAuto, Union[Key, Path]]]

Container = Union[None, List, Dict[Key, Any]]


def replace_ellipsis(name: str, path: Union[Path, Key]) -> Union[CleanPath, CleanKey]:
    """Fix all `...` in the path replacing then with the name."""
    if isinstance(path, ellipsis):
        return name
    if isinstance(path, (str, int)):
        return path
    return tuple(
        (name if isinstance(x, ellipsis) else x)
        for x in path
    )


def extend_container(root: Container, key: Key) -> None:
    if isinstance(root, list):
        if not isinstance(key, int):
            raise ValueError(f"Expected int, but got got {type(key)} (`{key}`) in field path")
        if len(root) < key + 1:
            root.extend([None] * (key - len(root) + 1))
    elif isinstance(key, int):
        raise ValueError(f"Expected str, but got {type(key)} (`{key}`) in field path")


def make_container(key: Key) -> Container:
    if isinstance(key, int):
        return [None] * (key + 1)
    else:
        return {}


def init_structure(paths: Iterable[Path]) -> Tuple[Container, Sequence[Tuple[Container, Key]]]:  # noqa C901,CCR001
    """
    Create empty structure that can be filled by described path
    Returns whole container itself and separate subcontainers for each path
    """
    root: List[Container] = [None]
    field_containers: List[Tuple[Container, Key]] = []
    for path in paths:
        current: Container = root
        prev_key: Key = 0
        for next_key in path:
            not_exist = False
            if current is None:
                raise ValueError
            if isinstance(current, dict):
                if not isinstance(prev_key, str):
                    raise ValueError(f"str expected, found {type(next_key)} (`{next_key}`)")
                if prev_key not in current:
                    not_exist = True
            if isinstance(current, List):
                if not isinstance(prev_key, int):
                    raise ValueError(f"int expected, found {type(next_key)} (`{next_key}`)")
                if current[prev_key] is None:
                    not_exist = True
            if not_exist:
                current[prev_key] = make_container(next_key)  # type: ignore
            else:
                extend_container(current[prev_key], next_key)  # type: ignore
            current = current[prev_key]  # type: ignore
            prev_key = next_key
        field_containers.append((current, prev_key))
    return root[0], field_containers
