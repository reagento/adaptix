def strip_alias(type_hint):
    try:
        return type_hint.__origin__
    except AttributeError:
        return type_hint


def get_args(type_hint):
    try:
        return list(type_hint.__args__)
    except AttributeError:
        return []


def is_subclass_soft(cls, classinfo) -> bool:
    try:
        return issubclass(cls, classinfo)
    except TypeError:
        return False


def is_new_type(tp) -> bool:
    return hasattr(tp, '__supertype__')


def is_annotated(tp) -> bool:
    return hasattr(tp, '__metadata__')
