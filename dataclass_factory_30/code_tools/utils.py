def has_literal_repr(obj: object) -> bool:
    if obj is None or obj is Ellipsis or obj is NotImplemented:
        return True

    obj_type = type(obj)
    if obj_type in (int, float, str, bytes, bool, bytearray, range):
        return True

    if obj_type in (list, tuple, set, frozenset):
        return all(has_literal_repr(el) for el in obj)  # type: ignore

    if obj_type == slice:
        return has_literal_repr(obj.start) and has_literal_repr(obj.step) and has_literal_repr(obj.stop)  # type: ignore

    if obj_type == dict:
        return all(
            has_literal_repr(key) and has_literal_repr(value)
            for key, value in obj.items()  # type: ignore
        )

    return False
