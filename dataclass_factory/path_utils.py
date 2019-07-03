from typing import Dict, List, Union, Iterable, Tuple

Key = Union[str, int]
Container = Union[None, List, Dict[Key, "Container"]]
Path = Tuple[Key, ...]


def extend_container(root: Container, key: Key) -> None:
    if isinstance(root, list):
        if not isinstance(key, int):
            raise ValueError("Expected int, but got `%s` in field path" % key)
        if len(root) < key:
            root.extend([None] * (key - len(root) + 1))
    elif isinstance(key, int):
        raise ValueError("Expected str, but got `%s` in field path" % key)


def make_container(key: Key) -> Container:
    if isinstance(key, int):
        return [None] * (key + 1)
    else:
        return {}


def init_structure(paths: Iterable[Path]) -> Container:
    root: Container = [None]
    for path in paths:
        current: Container = root
        prev_key: Key = 0
        for next_key in path:
            if current is None:
                raise ValueError
            elif isinstance(current, dict) and prev_key not in current:
                not_exist = True
            elif isinstance(current, List) and current[prev_key] is None:
                not_exist = True
            else:
                not_exist = False

            if not_exist:
                current[prev_key] = make_container(next_key)
            else:
                extend_container(current[prev_key], next_key)
            current = current[prev_key]
            prev_key = next_key
    return root[0]
