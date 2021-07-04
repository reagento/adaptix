from dataclass_factory_30.common import TypeHint


def strip_alias(type_hint: TypeHint):
    try:
        return type_hint.__origin__ # noqa
    except AttributeError:
        return type_hint


def get_args(type_hint: TypeHint) -> list:
    try:
        return list(type_hint.__args__)  # noqa
    except AttributeError:
        return []


def is_subclass_soft(cls, classinfo) -> bool:
    """Acts like builtin issubclass, but returns False instead of rising TypeError
    """
    try:
        return issubclass(cls, classinfo)
    except TypeError:
        return False


def is_new_type(tp) -> bool:
    return hasattr(tp, '__supertype__')


def is_annotated(tp) -> bool:
    return hasattr(tp, '__metadata__')
