import collections
import re
from collections import abc as c_abc
from collections import defaultdict
from typing import Tuple, Any, Dict, AnyStr, NewType, ClassVar, Final, Literal, Union, Optional, Iterable, \
    List

from typing_extensions import Annotated

from ..common import TypeHint

NormalizedType = Tuple[TypeHint, Tuple[Any, ...]]

TYPE_PARAM_NO: Dict[TypeHint, int] = defaultdict(
    lambda: 0,
    {
        type: 1,
        list: 1,
        set: 1,
        frozenset: 1,
        collections.Counter: 1,
        collections.deque: 1,
        dict: 2,
        defaultdict: 2,
        collections.OrderedDict: 2,
        collections.ChainMap: 2,
    }
)

ONE_ANY_STR_PARAM = {
    re.Pattern, re.Match
}

FORBID_ZERO_ARGS = {
    ClassVar, Final, Annotated,
    Literal, Union, Optional
}

N_ANY = (Any, ())
NoneType = type(None)


def strip_alias(type_hint):
    try:
        return type_hint.__origin__
    except AttributeError:
        return type_hint


def get_args(type_hint):
    try:
        return type_hint.__args__
    except AttributeError:
        return ()


def is_subclass_soft(cls, classinfo) -> bool:
    try:
        return issubclass(cls, classinfo)
    except TypeError:
        return False


def _n_many_types(tps):
    return tuple(
        normalize_type(tp) for tp in tps
    )


def _merge_literals(args):
    result = []
    lit_args = None
    for (origin, sub_args) in args:
        if origin == Literal:
            if lit_args is None:
                lit_args = [sub_args]
            else:
                lit_args.append((origin, sub_args))
        else:
            if lit_args is not None:
                result.extend(_remove_dups(lit_args))
                lit_args = None
            result.append((origin, sub_args))

    if lit_args is not None:
        result.extend(_remove_dups(lit_args))

    return tuple(result)


def normalize_type(tp) -> Tuple[Any, Tuple[Any, ...]]:
    origin = strip_alias(tp)
    args = get_args(tp)

    if origin is None or origin is NoneType:
        return None, ()

    if hasattr(tp, '__metadata__'):
        return Annotated, (normalize_type(origin),) + tp.__metadata__

    if is_subclass_soft(origin, tuple):
        if tp in (tuple, Tuple):  # not subscribed values
            return tuple, (N_ANY, ...)

        # >>> Tuple[()].__args__
        # ((),)
        # >>> tuple[()].__args__
        # ()
        if args == () or args == ((), ):
            return tuple, ()

        fixed_args = args[-1] is ...
        if fixed_args:
            return origin, _n_many_types(args[:-1]) + (...,)

        return origin, _n_many_types(args)

    if origin == NewType:
        raise ValueError('NewType must be instantiating')

    if args == ():
        if origin in ONE_ANY_STR_PARAM:
            return origin, ((AnyStr,),)

        if origin in FORBID_ZERO_ARGS:
            raise ValueError(f'{origin} must be subscribed')

        if origin == c_abc.Callable:
            return origin, ([...], N_ANY)

        return origin, (N_ANY,) * TYPE_PARAM_NO[origin]

    if origin == Literal:
        if args == (None,):  # Literal[None] converted to None
            return None, ()
        return origin, args

    if origin == c_abc.Callable:
        if args[0] is ...:
            call_args = ...
        else:
            call_args = list(map(normalize_type, args[:-1]))  # type: ignore
        return origin, (call_args, normalize_type(args[-1]))

    if origin == Union:
        norm_args = _n_many_types(args)
        unique_n_args = tuple(_remove_dups(norm_args))
        merged_args = _merge_literals(unique_n_args)

        if len(merged_args) == 1:
            return merged_args[0]
        return origin, merged_args

    return origin, _n_many_types(args)


def _remove_dups(inp: Iterable) -> List:
    in_set = set()
    result = []
    for item in inp:
        if item not in in_set:
            result.append(item)
            in_set.add(item)
    return result
