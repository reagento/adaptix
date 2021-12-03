import collections
import re
from abc import ABC, abstractmethod
from collections import defaultdict, abc as c_abc
from dataclasses import InitVar
from typing import (
    Any, Optional, List, Dict,
    ClassVar, Final, Literal,
    Union, NoReturn, Generic,
    TypeVar, Tuple, NewType,
    AnyStr, Iterable, ForwardRef,
    Hashable,
)

from typing_extensions import Annotated

from .basic_utils import strip_alias, get_args, is_new_type, is_annotated, is_subclass_soft, is_user_defined_generic
from ..common import TypeHint


class BaseNormType(Hashable, ABC):
    @property
    @abstractmethod
    def origin(self) -> Any:
        pass

    @property
    @abstractmethod
    def args(self) -> List[Any]:
        pass

    @property
    @abstractmethod
    def source(self) -> TypeHint:
        pass


class NormType(BaseNormType):
    __slots__ = ('_source', '_origin', '_list_args', '_tuple_args')

    def __init__(
        self,
        origin: TypeHint,
        args: Optional[List] = None,
        *,
        source: TypeHint = None
    ):
        if args is None:
            args = []

        self._source = source
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

    @property
    def source(self) -> TypeHint:
        return self._source

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


class NormTV(BaseNormType):
    __slots__ = ('_var', '_is_template', '_constraints', '_bound')

    def __init__(self, type_var: Any, *, is_template: bool = False):
        self._var = type_var
        self._is_template = is_template
        self._constraints = tuple(
            _dedup(_norm_iter(type_var.__constraints__))
        )
        if type_var.__bound__ is None:
            self._bound = None
        else:
            self._bound = normalize_type(type_var.__bound__)

    @property
    def origin(self) -> Any:
        return self._var

    @property
    def args(self) -> List[Any]:
        return []

    @property
    def source(self) -> TypeHint:
        return self._var

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
    def constraints(self) -> Tuple['BaseNormType', ...]:
        return self._constraints

    @property
    def bound(self) -> Optional['BaseNormType']:
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
    Literal, Union, Optional,
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


def _unfold_union_args(norm_args: List[BaseNormType]) -> List[BaseNormType]:
    result = []
    for norm in norm_args:
        if norm.origin == Union:
            result.extend(norm.args)
        else:
            result.append(norm)
    return result


def _dedup(inp: Iterable) -> List:
    in_set = set()
    result = []
    for item in inp:
        if item not in in_set:
            result.append(item)
            in_set.add(item)
    return result


def _create_norm_literal(args):
    dedup_args = _dedup(args)
    return NormType(
        Literal, dedup_args,
        source=Literal.__getitem__(
            tuple(dedup_args)  # type: ignore
        )
    )


def _merge_literals(args: List[NormType]) -> List[NormType]:
    result = []
    lit_args = []
    for norm in args:
        if norm.origin == Literal:
            lit_args.extend(norm.args)
        else:
            if lit_args:
                result.append(
                    _create_norm_literal(lit_args)
                )
                lit_args = []

            result.append(norm)

    if lit_args:
        result.append(
            _create_norm_literal(lit_args)
        )

    return result


T_co = TypeVar('T_co', covariant=True)


def normalize_type(tp: TypeHint) -> BaseNormType:
    origin = strip_alias(tp)
    args = get_args(tp)

    if origin in (NewType, TypeVar):
        raise ValueError(f'{origin} must be instantiating')

    if origin == InitVar:
        raise ValueError(f'{origin} must be subscribed')

    if not (
        isinstance(origin, (type, TypeVar, InitVar))
        or origin in ALLOWED_ORIGINS
        or is_new_type(tp)
    ):
        raise ValueError(f'Can not normalize {tp}')

    if origin is None or origin is NoneType:
        return NormType(None, source=tp)

    if is_annotated(tp):
        return NormType(
            Annotated, [normalize_type(origin)] + list(tp.__metadata__),
            source=tp
        )

    if isinstance(origin, TypeVar):
        return NormTV(origin)

    if isinstance(origin, InitVar):
        # origin is InitVar[T]
        return NormType(InitVar, [normalize_type(origin.type)], source=tp)

    if is_subclass_soft(origin, tuple):
        if tp in (tuple, Tuple):  # not subscribed values
            return NormType(
                tuple, [NormTV(T_co, is_template=True), ...],
                source=tp
            )

        # >>> Tuple[()].__args__
        # ((),)
        # >>> tuple[()].__args__
        # ()
        if not args or args == [()]:
            return NormType(tuple, source=tp)

        is_var_args = args[-1] is ...
        if is_var_args:
            return NormType(
                origin, _norm_iter(args[:-1]) + [...],
                source=tp,
            )

        return NormType(origin, _norm_iter(args), source=tp)

    if is_user_defined_generic(origin):
        if not args:
            params = origin.__parameters__  # type: ignore
            return NormType(
                origin, [NormTV(p, is_template=True) for p in params],
                source=tp,
            )
        return NormType(origin, _norm_iter(args), source=tp)

    if origin == c_abc.Callable:
        if not args:
            return NormType(
                origin, [..., NormTV(T_co, is_template=True)], source=tp
            )

        if args[0] is ...:
            call_args = ...
        else:
            call_args = list(map(normalize_type, args[:-1]))  # type: ignore
        return NormType(
            origin, [call_args, normalize_type(args[-1])], source=tp
        )

    if not args:
        if origin in ONE_ANY_STR_PARAM:
            return NormType(
                origin, [NormTV(AnyStr, is_template=True)], source=tp
            )

        if origin in FORBID_ZERO_ARGS:
            raise ValueError(f'{origin} must be subscribed')

        return NormType(
            origin,
            [
                NormTV(T_co, is_template=True)
                for _ in range(TYPE_PARAM_NO[origin])
            ],
            source=tp,
        )

    if origin == Literal:
        if args == [None]:  # Literal[None] converted to None
            return NormType(None, source=tp)
        return NormType(origin, args, source=tp)

    if origin == Union:
        norm_args = _norm_iter(args)
        unfolded_n_args = _unfold_union_args(norm_args)
        unique_n_args = _dedup(unfolded_n_args)
        merged_n_args = _merge_literals(unique_n_args)

        if len(merged_n_args) == 1:
            return merged_n_args[0]
        return NormType(origin, merged_n_args, source=tp)

    if is_subclass_soft(origin, type):
        norm = normalize_type(args[0])
        if norm.origin == Union:
            return NormType(
                Union, [NormType(type, [arg]) for arg in norm.args],
                source=tp
            )

    return NormType(origin, _norm_iter(args), source=tp)
