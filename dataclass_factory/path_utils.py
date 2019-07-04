from typing import Dict, List, Union, Iterable, Tuple, Sequence, Any

Key = Union[str, int]
Container = Union[None, List, Dict[Key, Any]]
Path = Tuple[Key, ...]


def extend_container(root: Container, key: Key) -> None:
    if isinstance(root, list):
        if not isinstance(key, int):
            raise ValueError("Expected int, but got `%s` in field path" % key)
        if len(root) < key + 1:
            root.extend([None] * (key - len(root) + 1))
    elif isinstance(key, int):
        raise ValueError("Expected str, but got `%s` in field path" % key)


def make_container(key: Key) -> Container:
    if isinstance(key, int):
        return [None] * (key + 1)
    else:
        return {}


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
                    raise ValueError("str expected, found %s" % next_key)
                if prev_key not in current:
                    not_exist = True
            if isinstance(current, List):
                if not isinstance(prev_key, int):
                    raise ValueError("int expected, found %s" % next_key)
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
