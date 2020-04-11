from typing import Dict, List, Union, Iterable, Tuple, Sequence, Any, Optional, TYPE_CHECKING

# https://github.com/python/typing/issues/684#issuecomment-548203158
if TYPE_CHECKING:
    from enum import Enum


    class EllipsisType(Enum):
        Ellipsis = "..."


    Ellipsis = EllipsisType.Ellipsis
else:
    EllipsisType = type(Ellipsis)

Key = Union[str, int, EllipsisType]
Container = Union[None, List, Dict[Key, Any]]
Path = Tuple[Key, ...]
NameMapping = Optional[Dict[str, Union[Key, Path]]]


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


def fix_name_mapping_ellipsis(name_mapping: NameMapping) -> NameMapping:
    if not name_mapping:
        return name_mapping
    return {
        name: fix_ellipsis(name, path)
        for name, path in name_mapping.items()
    }


def fix_ellipsis(name: str, path: Union[Path, Key]) -> Union[Path, Key]:
    if path is Ellipsis:
        return name
    if isinstance(path, str):
        return path
    if isinstance(path, int):
        return path
    return tuple(
        name if x is Ellipsis else x
        for x in path
    )


def init_structure(paths: Iterable[Path]) -> Tuple[Container, Sequence[Tuple[Container, Key]]]:
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
