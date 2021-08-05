import collections
import re
from collections import defaultdict, abc as c_abc
from typing import (
    Any, Optional, List, Dict,
    ClassVar, Final, Literal,
    Union, NoReturn, Generic,
    TypeVar, Tuple, NewType,
    AnyStr, Iterable, ForwardRef
)

from typing_extensions import Annotated

from .utils import strip_alias, get_args, is_new_type, is_annotated, is_subclass_soft
from ..common import TypeHint


class NormType:
    __slots__ = ('_origin', '_list_args', '_tuple_args')

    def __init__(self, origin: TypeHint, args: Optional[List] = None):
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


class NormTV:
    __slots__ = ('_var', '_is_template', '_constraints', '_bound')

    def __init__(self, type_var: Any, *, is_template: bool = False):
        self._var = type_var
        self._is_template = is_template
        self._constraints = tuple(_norm_iter(type_var.__constraints__))
        if type_var.__bound__ is None:
            self._bound = None
        else:
            self._bound = normalize_type(type_var.__bound__)

    def __getattr__(self, item):
        return getattr(self._var, item)

    @property
    def name(self) -> str:
        return self._var.__name__

    @property
    def covariant(self) -> bool:
        return self._var.__covariant__

    @property
    def contravariant(self) -> bool:
        return self._var.__contravariant__

    @property
    def invariant(self) -> bool:
        return not (
            self.covariant or self.contravariant
        )

    @property
    def constraints(self) -> Tuple['AnyNormType', ...]:
        return self._constraints

    @property
    def bound(self) -> Optional['AnyNormType']:
        return self._bound

    @property
    def is_template(self) -> bool:
        return self._is_template

    def __repr__(self):
        return f'{type(self).__name__}({self._var}, is_template={self._is_template})'

    def __hash__(self):
        return hash((self._var, self._is_template))

    def __eq__(self, other):
        if isinstance(other, NormTV):
            return (
                self._var == other._var
                and
                self._is_template == other._is_template
            )
        return NotImplemented


AnyNormType = Union[NormType, NormTV]

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
    Literal, Union, Generic,
    ForwardRef
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


T_co = TypeVar('T_co', covariant=True)
T_contra = TypeVar('T_contra', contravariant=True)


def normalize_type(tp: TypeHint) -> AnyNormType:
    origin = strip_alias(tp)
    args = get_args(tp)

    if origin == NewType:
        raise ValueError('NewType must be instantiating')

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

    if isinstance(origin, TypeVar):
        return NormTV(origin)

    if is_subclass_soft(origin, tuple):
        if tp in (tuple, Tuple):  # not subscribed values
            return NormType(tuple, [NormTV(T_co, is_template=True), ...])

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

    if is_subclass_soft(origin, Generic):
        if not args:
            params = origin.__parameters__  # type: ignore
            return NormType(
                origin, [NormTV(p, is_template=True) for p in params]
            )
        return NormType(origin, _norm_iter(args))

    if origin == c_abc.Callable:
        if not args:
            return NormType(origin, [..., NormTV(T_co, is_template=True)])

        if args[0] is ...:
            call_args = ...
        else:
            call_args = list(map(normalize_type, args[:-1]))  # type: ignore
        return NormType(
            origin, [call_args, normalize_type(args[-1])]
        )

    if not args:
        if origin in ONE_ANY_STR_PARAM:
            return NormType(
                origin, [NormTV(AnyStr, is_template=True)]
            )

        if origin in FORBID_ZERO_ARGS:
            raise ValueError(f'{origin} must be subscribed')

        return NormType(
            origin,
            [
                NormTV(T_co, is_template=True)
                for _ in range(TYPE_PARAM_NO[origin])
            ]
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
