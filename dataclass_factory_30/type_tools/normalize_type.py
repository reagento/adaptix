import collections
import re
from collections import defaultdict, abc as c_abc
from typing import (
    Any, Optional, List, Dict,
    ClassVar, Final, Literal,
    Union, NoReturn, Generic,
    TypeVar, Tuple, NewType,
    AnyStr, Iterable
)

from typing_extensions import Annotated

from .utils import strip_alias, get_args, is_new_type, is_annotated, is_subclass_soft
from ..common import TypeHint


class NormType:
    __slots__ = ('_origin', '_list_args', '_tuple_args')

    def __init__(self, origin: Any, args: Optional[List[Any]] = None):
        if args is None:
            args = []

        self._origin = origin
        self._list_args = args
        self._tuple_args = tuple(
            tuple(arg) if isinstance(arg, list) else arg
            for arg in args
        )

    @property
    def origin(self) -> Any:
        return self._origin

    @property
    def args(self) -> List[Any]:
        return self._list_args

    def __hash__(self):
        return hash((self._origin, self._tuple_args))

    def __eq__(self, other):
        if isinstance(other, NormType):
            return (
                self._origin == other._origin
                and
                self._tuple_args == other._tuple_args
            )
        return False

    def __repr__(self):
        return f'{type(self).__name__}({self.origin}, {self.args})'

    def __iter__(self):
        return iter((self.origin, self.args))


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
ALLOWED_ORIGINS = {
    Any, None, NoReturn,
    ClassVar, Final, Annotated,
    Literal, Union, Generic
}
NoneType = type(None)


def _norm_iter(tps):
    return [normalize_type(tp) for tp in tps]


def _dedup(inp: Iterable) -> List:
    in_set = set()
    result = []
    for item in inp:
        if item not in in_set:
            result.append(item)
            in_set.add(item)
    return result


def _merge_literals(args: List[NormType]) -> List[NormType]:
    result = []
    lit_args = []
    for norm in args:
        if norm.origin == Literal:
            lit_args.extend(norm.args)
        else:
            if lit_args:
                result.append(
                    NormType(Literal, _dedup(lit_args))
                )
                lit_args = []

            result.append(norm)

    if lit_args:
        result.append(
            NormType(Literal, _dedup(lit_args))
        )

    return result


def normalize_type(tp) -> NormType:
    origin = strip_alias(tp)
    args = get_args(tp)

    if not (
        isinstance(origin, type)
        or isinstance(origin, TypeVar)
        or origin in ALLOWED_ORIGINS
        or is_new_type(tp)
    ):
        raise ValueError(f'Can not normalize {tp}')

    if origin is None or origin is NoneType:
        return NormType(None)

    if is_annotated(tp):
        return NormType(
            Annotated, [normalize_type(origin)] + list(tp.__metadata__)
        )

    if is_subclass_soft(origin, tuple):
        if tp in (tuple, Tuple):  # not subscribed values
            return NormType(tuple, [NormType(Any), ...])

        # >>> Tuple[()].__args__
        # ((),)
        # >>> tuple[()].__args__
        # ()
        if not args or args == [()]:
            return NormType(tuple)

        fixed_args = args[-1] is ...
        if fixed_args:
            return NormType(origin, _norm_iter(args[:-1]) + [...])

        return NormType(origin, _norm_iter(args))

    if origin == NewType:
        raise ValueError('NewType must be instantiating')

    if is_subclass_soft(origin, Generic):
        if not args:
            args = origin.__parameters__  # noqa
        return NormType(origin, _norm_iter(args))

    if origin == c_abc.Callable:
        if not args:
            return NormType(origin, [..., NormType(Any)])

        if args[0] is ...:
            call_args = ...
        else:
            call_args = list(map(normalize_type, args[:-1]))  # type: ignore
        return NormType(
            origin, [call_args, normalize_type(args[-1])]
        )

    if not args:
        if origin in ONE_ANY_STR_PARAM:
            return NormType(origin, [NormType(AnyStr)])

        if origin in FORBID_ZERO_ARGS:
            raise ValueError(f'{origin} must be subscribed')

        return NormType(
            origin, [NormType(Any)] * TYPE_PARAM_NO[origin]
        )

    if origin == Literal:
        if args == [None]:  # Literal[None] converted to None
            return NormType(None)
        return NormType(origin, args)

    if origin == Union:
        norm_args = _norm_iter(args)
        unique_n_args = _dedup(norm_args)
        merged_n_args = _merge_literals(unique_n_args)

        if len(merged_n_args) == 1:
            return merged_n_args[0]
        return NormType(origin, merged_n_args)

    return NormType(origin, _norm_iter(args))
