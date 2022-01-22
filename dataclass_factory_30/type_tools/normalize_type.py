import collections
import re
from abc import ABC, abstractmethod
from collections import defaultdict, abc as c_abc
from dataclasses import InitVar, dataclass
from enum import Enum
from typing import (
    Any, Optional, List,
    Dict, ClassVar, Final, Literal,
    Union, TypeVar, Tuple, Iterable,
    Hashable, Callable, Type, NewType,
    overload, NoReturn,
)

from typing_extensions import Annotated

from .basic_utils import (
    strip_alias, get_args, is_annotated,
    is_subclass_soft, is_user_defined_generic, is_new_type
)
from ..common import TypeHint


class BaseNormType(Hashable, ABC):
    @property
    @abstractmethod
    def origin(self) -> Any:
        pass

    @property
    @abstractmethod
    def args(self) -> Tuple[Any, ...]:
        pass

    @property
    @abstractmethod
    def source(self) -> TypeHint:
        pass


T = TypeVar('T')


class NormType(BaseNormType):
    __slots__ = ('_source', '_origin', '_args')

    def __init__(
        self,
        origin: TypeHint,
        args: Tuple[Hashable, ...],
        *,
        source: TypeHint
    ):
        self._source = source
        self._origin = origin
        self._args = args

    @property
    def origin(self) -> Any:
        return self._origin

    @property
    def args(self) -> Tuple[Any, ...]:
        return self._args

    @property
    def source(self) -> TypeHint:
        return self._source

    def __hash__(self):
        return hash((self._origin, self._args))

    def __eq__(self, other):
        if isinstance(other, NormType):
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


class Variance(Enum):
    INVARIANT = 0
    COVARIANT = 1
    CONTRAVARIANT = 2


@dataclass
class Bound:
    value: NormType


@dataclass
class Constraints:
    value: Tuple[NormType, ...]


TVLimit = Union[Bound, Constraints]


class NormTV(BaseNormType):
    __slots__ = ('_var', '_limit', '_variance')

    def __init__(self, type_var: TypeVar, limit: TVLimit):  # type: ignore
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
ANY_NT = NormType(Any, (), source=Any)


class ImplicitParamsFiller:
    ONE_ANY_STR_PARAM = {
        re.Pattern, re.Match
    }

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

    NORM_ANY_STR_PARAM = NormType(
        Union,
        (NormType(bytes, (), source=bytes), NormType(str, (), source=str)),
        source=Union[bytes, str],
    )

    def get_implicit_params(self, origin, normalizer: "TypeNormalizer") -> Tuple[NormType, ...]:
        if origin in self.ONE_ANY_STR_PARAM:
            return (self.NORM_ANY_STR_PARAM,)

        if is_user_defined_generic(origin):
            params: Iterable[TypeVar] = origin.__parameters__
            limits = [normalizer.normalize(p).limit for p in params]

            return tuple(
                _create_union(lim.value)
                if isinstance(lim, Constraints) else
                lim.value
                for lim in limits
            )

        count = self.TYPE_PARAM_CNT.get(origin, 0)

        return tuple(ANY_NT for _ in range(count))


def _create_union(args: Tuple[BaseNormType, ...]) -> NormType:
    return NormType(
        Union, args,
        source=Union.__getitem__(tuple(a.source for a in args))
    )


def _dedup(inp: Iterable) -> List:
    in_set = set()
    result = []
    for item in inp:
        if item not in in_set:
            result.append(item)
            in_set.add(item)
    return result


def _create_norm_literal(args: tuple):
    dedup_args = tuple(_dedup(args))
    return NormType(
        Literal, dedup_args,
        source=Literal.__getitem__(
            dedup_args  # type: ignore
        )
    )


def _replace_source_with_union(norm: NormType, sources: list) -> NormType:
    return NormType(
        origin=norm.origin,
        args=norm.args,
        source=Union.__getitem__(tuple(sources))
    )


NormAspect = Callable[['TypeNormalizer', Any, Any, tuple], Optional[BaseNormType]]


class AspectStorage(List[str]):
    def add(self, func: NormAspect) -> NormAspect:
        self.append(func.__name__)
        return func

    def copy(self) -> 'AspectStorage':
        return type(self)(super().copy())


class MustSubscribed(ValueError):
    pass


T_Norm = TypeVar('T_Norm', bound=BaseNormType)


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

    def _norm_iter(self, tps) -> Tuple[BaseNormType, ...]:
        return tuple(self.normalize(tp) for tp in tps)

    MUST_SUBSCRIBED_ORIGINS = {
        ClassVar, Final, Annotated,
        Literal, Union, Optional,
        InitVar
    }

    @_aspect_storage.add
    def _check_bad_input(self, tp, origin, args):
        if tp in self.MUST_SUBSCRIBED_ORIGINS:
            raise MustSubscribed(f"{tp} must be subscribed")

        if tp in (NewType, TypeVar):
            raise ValueError(f'{origin} must be instantiating')

    @_aspect_storage.add
    def _norm_none(self, tp, origin, args):
        if origin is None or origin is NoneType:
            return NormType(None, (), source=tp)

    @_aspect_storage.add
    def _norm_annotated(self, tp, origin, args):
        if is_annotated(tp):
            return NormType(
                Annotated,
                (self.normalize(origin), *tp.__metadata__),
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
            # origin is InitVar[T]
            return NormType(
                InitVar,
                (self.normalize(origin.type),),
                source=tp
            )

    @_aspect_storage.add
    def _norm_new_type(self, tp, origin, args):
        if is_new_type(tp):
            return NormType(tp, (), source=tp)

    @_aspect_storage.add
    def _norm_tuple(self, tp, origin, args):
        if is_subclass_soft(origin, tuple):
            if tp in (tuple, Tuple):  # not subscribed values
                return NormType(
                    tuple,
                    (ANY_NT, ...),
                    source=tp
                )

            # >>> Tuple[()].__args__
            # ((),)
            # >>> tuple[()].__args__
            # ()
            if not args or args == ((),):
                return NormType(tuple, (), source=tp)

            is_var_args = args[-1] is ...
            if is_var_args:
                return NormType(
                    origin, (*self._norm_iter(args[:-1]), ...),
                    source=tp,
                )

            return NormType(origin, self._norm_iter(args), source=tp)

    @_aspect_storage.add
    def _norm_callable(self, tp, origin, args):
        if origin == c_abc.Callable:
            if not args:
                return NormType(
                    origin, (..., ANY_NT), source=tp
                )

            if args[0] is ...:
                call_args = ...
            else:
                call_args = tuple(map(normalize_type, args[:-1]))
            return NormType(
                origin, (call_args, self.normalize(args[-1])), source=tp
            )

    @_aspect_storage.add
    def _norm_literal(self, tp, origin, args):
        if origin == Literal:
            if args == (None,):  # Literal[None] converted to None
                return NormType(None, (), source=tp)

            return NormType(origin, args, source=tp)

    def _unfold_union_args(self, norm_args: Iterable[T_Norm]) -> List[T_Norm]:
        result = []
        for norm in norm_args:
            if norm.origin == Union:
                result.extend(norm.args)
            else:
                result.append(norm)
        return result

    def _dedup_union_args(self, args: Iterable[BaseNormType]) -> Iterable[BaseNormType]:
        arg_to_pos: Dict[BaseNormType, int] = {}
        result: List[BaseNormType] = []
        args_source: List[List[TypeHint]] = []

        for item in args:
            if item in arg_to_pos:
                pos = arg_to_pos[item]
                args_source[pos].append(item.source)
            else:
                result.append(item)
                args_source.append([item.source])
                arg_to_pos[item] = len(result) - 1

        return [
            _replace_source_with_union(d_arg, sources)
            if len(sources) != 1 and isinstance(d_arg, NormType)
            else d_arg
            for d_arg, sources in zip(result, args_source)
        ]

    def _merge_literals(self, args: Iterable[T_Norm]) -> List[T_Norm]:
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

    @_aspect_storage.add
    def _norm_union(self, tp, origin, args):
        if origin == Union:
            norm_args = self._norm_iter(args)
            unfolded_n_args = self._unfold_union_args(norm_args)
            unique_n_args = self._dedup_union_args(unfolded_n_args)
            merged_n_args = self._merge_literals(unique_n_args)

            if len(merged_n_args) == 1:
                arg = merged_n_args[0]
                return NormType(origin=arg.origin, args=arg.args, source=tp)
            return NormType(origin, tuple(merged_n_args), source=tp)

    @_aspect_storage.add
    def _norm_type(self, tp, origin, args):
        if is_subclass_soft(origin, type) and args:
            norm = self.normalize(args[0])

            if norm.origin == Union:
                return NormType(
                    Union,
                    tuple(
                        NormType(type, (arg,), source=Type[arg.source])
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
            return NormType(origin, self._norm_iter(args), source=tp)

        params = self.imp_params_filler.get_implicit_params(
            origin, self
        )

        if not (
            params
            or isinstance(origin, type)
            or origin in self.ALLOWED_ZERO_PARAMS_ORIGINS
        ):
            raise ValueError(f'Can not normalize {tp}')

        return NormType(
            origin,
            params,
            source=tp,
        )


_STD_NORMALIZER = TypeNormalizer(ImplicitParamsFiller())


def normalize_type(tp: TypeHint) -> BaseNormType:
    return _STD_NORMALIZER.normalize(tp)
