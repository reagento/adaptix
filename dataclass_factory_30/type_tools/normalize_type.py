# pylint: disable=inconsistent-return-statements,comparison-with-callable
import collections
import re
import types
import typing
from abc import ABC, abstractmethod
from collections import abc as c_abc, defaultdict
from dataclasses import InitVar, dataclass
from enum import Enum, EnumMeta
from typing import (
    Any,
    Callable,
    ClassVar,
    DefaultDict,
    Final,
    Hashable,
    Iterable,
    List,
    Literal,
    NewType,
    NoReturn,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_args,
    overload,
)

from ..common import TypeHint, VarTuple
from ..feature_requirement import HAS_ANNOTATED, HAS_TYPE_UNION_OP
from .basic_utils import create_union, is_new_type, is_subclass_soft, is_user_defined_generic, strip_alias


class BaseNormType(Hashable, ABC):
    @property
    @abstractmethod
    def origin(self) -> Any:
        pass

    @property
    @abstractmethod
    def args(self) -> VarTuple[Any]:
        pass

    @property
    @abstractmethod
    def source(self) -> TypeHint:
        pass


T = TypeVar('T')


class _BasicNormType(BaseNormType, ABC):
    __slots__ = ('_source', '_args')

    def __init__(self, args: VarTuple[Any], *, source: TypeHint):
        self._source = source
        self._args = args

    @property
    def args(self) -> VarTuple[Any]:
        return self._args

    @property
    def source(self) -> TypeHint:
        return self._source

    def __hash__(self):
        return hash((self.origin, self._args))

    def __eq__(self, other):
        if isinstance(other, _BasicNormType):
            return (
                self.origin == other.origin
                and
                self._args == other._args
            )
        if isinstance(other, BaseNormType):
            return False
        return NotImplemented

    def __repr__(self):
        args_str = f" {list(self.args)}," if self.args else ""
        return f'<{type(self).__name__}({self.origin},{args_str} source={self._source})>'


class _NormType(BaseNormType):
    __slots__ = ('_source', '_origin', '_args')

    def __init__(self, origin: TypeHint, args: VarTuple[Any], *, source: TypeHint):
        self._source = source
        self._origin = origin
        self._args = args

    @property
    def origin(self) -> Any:
        return self._origin

    @property
    def args(self) -> VarTuple[Any]:
        return self._args

    @property
    def source(self) -> TypeHint:
        return self._source

    def __hash__(self):
        return hash((self._origin, self._args))

    def __eq__(self, other):
        if isinstance(other, _NormType):
            return (
                self._origin == other._origin
                and
                self._args == other._args
            )
        if isinstance(other, BaseNormType):
            return False
        return NotImplemented

    def __repr__(self):
        args_str = f" {list(self.args)}," if self.args else ""
        return f'<{type(self).__name__}({self.origin},{args_str} source={self._source})>'


class _UnionNormType(_BasicNormType):
    def __init__(self, args: VarTuple[Any], *, source: TypeHint):
        super().__init__(self._order_args(args), source=source)

    @property
    def origin(self) -> Any:
        return Union

    # ensure stable order of args during one interpreter session
    def _make_orderable(self, obj: object) -> str:
        if isinstance(obj, BaseNormType):
            return f"{obj.origin} {[self._make_orderable(arg) for arg in obj.args]}"
        return str(obj)

    def _order_args(self, args: VarTuple[BaseNormType]) -> VarTuple[BaseNormType]:
        args_list = list(args)
        args_list.sort(key=self._make_orderable)
        return tuple(args_list)


def _type_and_value_iter(args):
    return [(type(arg), arg) for arg in args]


LiteralArg = Union[str, int, bytes, Enum]


class _LiteralNormType(_BasicNormType):
    def __init__(self, args: VarTuple[Any], *, source: TypeHint):
        super().__init__(self._order_args(args), source=source)

    @property
    def origin(self) -> Any:
        return Literal

    # ensure stable order of args during one interpreter session
    def _make_orderable(self, obj: LiteralArg) -> str:
        return f"{type(obj)}{obj.name}" if isinstance(obj, Enum) else repr(obj)

    def _order_args(self, args: VarTuple[LiteralArg]) -> VarTuple[LiteralArg]:
        args_list = list(args)
        args_list.sort(key=self._make_orderable)
        return tuple(args_list)

    def __eq__(self, other):
        if isinstance(other, _LiteralNormType):
            return _type_and_value_iter(self._args) == _type_and_value_iter(other._args)
        if isinstance(other, BaseNormType):
            return False
        return NotImplemented

    __hash__ = _BasicNormType.__hash__


class _AnnotatedNormType(_BasicNormType):
    @property
    def origin(self) -> Any:
        return typing.Annotated

    __slots__ = _BasicNormType.__slots__ + ('_hash',)

    def __init__(self, args: VarTuple[Hashable], *, source: TypeHint):
        super().__init__(args, source=source)
        self._hash = self._calc_hash()

    # calculate hash even if one of Annotated metadata is not hashable
    def _calc_hash(self) -> int:
        lst = [self.origin]
        for arg in self._args:
            try:
                arg_hash = hash(arg)
            except TypeError:
                pass
            else:
                lst.append(arg_hash)
        return hash(tuple(lst))

    def __hash__(self):
        return self._hash


def make_norm_type(
    origin: TypeHint,
    args: VarTuple[Hashable],
    *,
    source: TypeHint
):
    if origin == Union:
        if not all(isinstance(arg, BaseNormType) for arg in args):
            raise TypeError
        return _UnionNormType(args, source=source)  # type: ignore
    if origin == Literal:
        if not all(type(arg) in [int, bool, str, bytes] or isinstance(type(arg), EnumMeta) for arg in args):
            raise TypeError
        return _LiteralNormType(args, source=source)  # type: ignore
    if HAS_ANNOTATED and origin == typing.Annotated:
        return _AnnotatedNormType(args, source=source)
    if isinstance(origin, TypeVar):
        raise TypeError
    return _NormType(origin, args, source=source)


class Variance(Enum):
    INVARIANT = 0
    COVARIANT = 1
    CONTRAVARIANT = 2


@dataclass
class Bound:
    value: BaseNormType


@dataclass
class Constraints:
    value: VarTuple[BaseNormType]


TVLimit = Union[Bound, Constraints]


class NormTV(BaseNormType):
    __slots__ = ('_var', '_limit', '_variance')

    def __init__(self, type_var: TypeVar, limit: TVLimit):
        self._var = type_var
        self._limit = limit

        if type_var.__covariant__:
            self._variance = Variance.COVARIANT
        if type_var.__contravariant__:
            self._variance = Variance.CONTRAVARIANT
        self._variance = Variance.INVARIANT

    @property
    def origin(self) -> TypeVar:
        return self._var

    @property
    def args(self) -> Tuple[()]:
        return ()

    @property
    def source(self) -> TypeHint:
        return self._var

    @property
    def name(self) -> str:
        return self._var.__name__

    @property
    def variance(self) -> Variance:
        return self._variance

    @property
    def limit(self) -> TVLimit:
        return self._limit

    def __repr__(self):
        return f'<{type(self).__name__}({self._var})>'

    def __hash__(self):
        return hash(self._var)

    def __eq__(self, other):
        if isinstance(other, NormTV):
            return self._var == other._var
        if isinstance(other, BaseNormType):
            return False
        return NotImplemented


NoneType = type(None)
ANY_NT = _NormType(Any, (), source=Any)


class ImplicitParamsFiller:
    ONE_ANY_STR_PARAM = [re.Pattern, re.Match]

    TYPE_PARAM_CNT = {
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
        **{el: 1 for el in ONE_ANY_STR_PARAM}
    }

    NORM_ANY_STR_PARAM = _UnionNormType(
        (_NormType(bytes, (), source=bytes), _NormType(str, (), source=str)),
        source=Union[bytes, str],
    )

    def get_implicit_params(self, origin, normalizer: "TypeNormalizer") -> VarTuple[BaseNormType]:
        if origin in self.ONE_ANY_STR_PARAM:
            return (self.NORM_ANY_STR_PARAM,)

        if is_user_defined_generic(origin):
            params: Iterable[TypeVar] = origin.__parameters__
            limits = [normalizer.normalize(p).limit for p in params]

            return tuple(
                _create_norm_union(lim.value)
                if isinstance(lim, Constraints) else
                lim.value
                for lim in limits
            )

        count = self.TYPE_PARAM_CNT.get(origin, 0)

        return tuple(ANY_NT for _ in range(count))


def _create_norm_union(args: VarTuple[BaseNormType]) -> BaseNormType:
    return _UnionNormType(args, source=create_union(tuple(a.source for a in args)))


def _dedup(inp: Iterable) -> List:
    in_set = set()
    result = []
    for item in inp:
        if item not in in_set:
            result.append(item)
            in_set.add(item)
    return result


def _create_norm_literal(args: Iterable):
    dedup_args = tuple(_dedup(args))
    return _LiteralNormType(
        dedup_args,
        source=Literal.__getitem__(  # pylint: disable=unnecessary-dunder-call
            dedup_args  # type: ignore
        )
    )


def _replace_source_with_union(norm: _NormType, sources: list) -> _NormType:
    return make_norm_type(
        origin=norm.origin,
        args=norm.args,
        source=create_union(tuple(sources))
    )


NormAspect = Callable[['TypeNormalizer', Any, Any, tuple], Optional[BaseNormType]]


class AspectStorage(List[str]):
    def add(self, func: NormAspect) -> NormAspect:
        self.append(func.__name__)
        return func

    def copy(self) -> 'AspectStorage':
        return type(self)(super().copy())


class NotSubscribedError(ValueError):
    pass


N = TypeVar('N', bound=BaseNormType)


class TypeNormalizer:
    def __init__(self, imp_params_filler: ImplicitParamsFiller):
        self.imp_params_filler = imp_params_filler

    @overload
    def normalize(self, tp: TypeVar) -> NormTV:
        pass

    @overload
    def normalize(self, tp: TypeHint) -> BaseNormType:
        pass

    def normalize(self, tp: TypeHint) -> BaseNormType:
        origin = strip_alias(tp)
        args = get_args(tp)

        for attr_name in self._aspect_storage:
            result = getattr(self, attr_name)(tp, origin, args)
            if result is not None:
                return result

        raise RuntimeError

    _aspect_storage = AspectStorage()

    def _norm_iter(self, tps) -> VarTuple[BaseNormType]:
        return tuple(self.normalize(tp) for tp in tps)

    MUST_SUBSCRIBED_ORIGINS = [
        ClassVar, Final, Literal,
        Union, Optional, InitVar,
    ]

    if HAS_ANNOTATED:
        MUST_SUBSCRIBED_ORIGINS.append(typing.Annotated)

    @_aspect_storage.add
    def _check_bad_input(self, tp, origin, args):
        if tp in self.MUST_SUBSCRIBED_ORIGINS:
            raise NotSubscribedError(f"{tp} must be subscribed")

        if tp in (NewType, TypeVar):
            raise ValueError(f'{origin} must be instantiating')

    @_aspect_storage.add
    def _norm_none(self, tp, origin, args):
        if origin is None or origin is NoneType:
            return _NormType(None, (), source=tp)

    if HAS_ANNOTATED:
        @_aspect_storage.add
        def _norm_annotated(self, tp, origin, args):
            if origin == typing.Annotated:
                return _AnnotatedNormType(
                    (self.normalize(args[0]), *args[1:]),
                    source=tp
                )

    @_aspect_storage.add
    def _norm_type_var(self, tp, origin, args):
        if isinstance(origin, TypeVar):
            limit: TVLimit

            if origin.__constraints__:
                limit = Constraints(
                    tuple(  # type: ignore
                        self._dedup_union_args(
                            self._norm_iter(origin.__constraints__)
                        )
                    )
                )
            elif origin.__bound__ is None:
                limit = Bound(ANY_NT)
            else:
                limit = Bound(self.normalize(origin.__bound__))  # type: ignore

            return NormTV(
                type_var=origin,
                limit=limit,
            )

    @_aspect_storage.add
    def _norm_init_var(self, tp, origin, args):
        if isinstance(origin, InitVar):
            # this origin is InitVar[T]
            return _NormType(
                InitVar,
                (self.normalize(origin.type),),
                source=tp
            )

    @_aspect_storage.add
    def _norm_new_type(self, tp, origin, args):
        if is_new_type(tp):
            return _NormType(tp, (), source=tp)

    @_aspect_storage.add
    def _norm_tuple(self, tp, origin, args):
        if origin == tuple:
            if tp in (tuple, Tuple):  # not subscribed values
                return _NormType(
                    tuple,
                    (ANY_NT, ...),
                    source=tp
                )

            # >>> Tuple[()].__args__ == ((),)
            # >>> tuple[()].__args__ == ()
            if not args or args == ((),):
                return _NormType(tuple, (), source=tp)

            is_var_args = args[-1] is ...
            if is_var_args:
                return _NormType(
                    tuple, (*self._norm_iter(args[:-1]), ...),
                    source=tp,
                )

            return _NormType(tuple, self._norm_iter(args), source=tp)

    @_aspect_storage.add
    def _norm_callable(self, tp, origin, args):
        if origin == c_abc.Callable:
            if not args:
                return _NormType(
                    c_abc.Callable, (..., ANY_NT), source=tp
                )

            if args[0] is ...:
                call_args = ...
            else:
                call_args = tuple(map(normalize_type, args[0]))
            return _NormType(
                c_abc.Callable, (call_args, self.normalize(args[-1])), source=tp
            )

    @_aspect_storage.add
    def _norm_literal(self, tp, origin, args):
        if origin == Literal:
            if args == (None,):  # Literal[None] converted to None
                return _NormType(None, (), source=tp)

            if None in args:
                args_without_none = list(args)
                args_without_none.remove(None)

                return _UnionNormType(
                    (
                        _NormType(None, (), source=Literal[None]),
                        _create_norm_literal(args_without_none),
                    ),
                    source=tp
                )

            return _LiteralNormType(args, source=tp)

    def _unfold_union_args(self, norm_args: Iterable[N]) -> List[N]:
        result: List[N] = []
        for norm in norm_args:
            if norm.origin == Union:
                result.extend(norm.args)
            else:
                result.append(norm)
        return result

    def _dedup_union_args(self, args: Iterable[BaseNormType]) -> Iterable[BaseNormType]:
        args_to_sources: DefaultDict[BaseNormType, List[Any]] = defaultdict(list)

        for arg in args:
            args_to_sources[arg].append(arg.source)

        return [
            _replace_source_with_union(arg, sources)
            if len(sources) != 1 and isinstance(arg, _NormType)
            else arg
            for arg, sources in args_to_sources.items()
        ]

    def _merge_literals(self, args: Iterable[N]) -> List[N]:
        result = []
        lit_args: List[N] = []
        for norm in args:
            if norm.origin == Literal:
                lit_args.extend(norm.args)
            else:
                result.append(norm)

        if lit_args:
            result.append(_create_norm_literal(lit_args))
        return result

    _UNION_ORIGINS: List[Any] = [Union]

    if HAS_TYPE_UNION_OP:
        _UNION_ORIGINS.append(types.UnionType)

    @_aspect_storage.add
    def _norm_union(self, tp, origin, args):
        if origin in self._UNION_ORIGINS:
            norm_args = self._norm_iter(args)
            unfolded_n_args = self._unfold_union_args(norm_args)
            unique_n_args = self._dedup_union_args(unfolded_n_args)
            merged_n_args = self._merge_literals(unique_n_args)

            if len(merged_n_args) == 1:
                arg = merged_n_args[0]
                return make_norm_type(origin=arg.origin, args=arg.args, source=tp)
            return _UnionNormType(tuple(merged_n_args), source=tp)

    @_aspect_storage.add
    def _norm_type(self, tp, origin, args):
        if is_subclass_soft(origin, type) and args:
            norm = self.normalize(args[0])

            if norm.origin == Union:
                return _UnionNormType(
                    tuple(
                        _NormType(type, (arg,), source=Type[arg.source])
                        for arg in norm.args
                    ),
                    source=tp
                )

    ALLOWED_ZERO_PARAMS_ORIGINS = {
        Any, NoReturn,
    }

    @_aspect_storage.add
    def _norm_other(self, tp, origin, args):
        if args:
            return _NormType(origin, self._norm_iter(args), source=tp)

        params = self.imp_params_filler.get_implicit_params(
            origin, self
        )

        if not (
            params
            or isinstance(origin, type)
            or origin in self.ALLOWED_ZERO_PARAMS_ORIGINS
        ):
            raise ValueError(f'Can not normalize {tp}')

        return _NormType(
            origin,
            params,
            source=tp,
        )


_STD_NORMALIZER = TypeNormalizer(ImplicitParamsFiller())


def normalize_type(tp: TypeHint) -> BaseNormType:
    return _STD_NORMALIZER.normalize(tp)
