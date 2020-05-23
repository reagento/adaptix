from typing import Type, Dict, Any, get_type_hints

from .type_detection import is_generic_concrete


def fill_type_args(args: Dict[Type, Type], type_: Type, localns: Dict) -> Type:
    type_ = args.get(type_, type_)
    if is_generic_concrete(type_):
        type_args = tuple(
            args.get(a, a) for a in type_.__args__
        )
        type_ = type_.__origin__[type_args]
    return localns.get(type_, type_)


def resolve_hints(type_: Any, localns: Dict):
    if not is_generic_concrete(type_):
        return {
            name: localns.get(fieldtype, fieldtype)
            for name, fieldtype in get_type_hints(type_, None, localns).items()
        }
    hints = get_type_hints(type_.__origin__, None, localns)
    args = dict(zip(type_.__origin__.__parameters__, type_.__args__))
    return {
        name: fill_type_args(args, fieldtype, localns)
        for name, fieldtype in hints.items()
    }


def resolve_init_hints(type_: Any, localns: Dict):
    if not is_generic_concrete(type_):
        return get_type_hints(type_.__init__, localns=localns)
    hints = get_type_hints(type_.__origin__.__init__, localns=localns)
    args = dict(zip(type_.__self__.__origin__.__parameters__, type_.__self__.__args__))
    return {
        name: fill_type_args(args, type, localns)
        for name, type in hints.items()
    }
