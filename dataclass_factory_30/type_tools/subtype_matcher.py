from abc import ABC, abstractmethod
from collections import abc as c_abc
from copy import copy
from dataclasses import dataclass, replace
from typing import (
    Dict, TypeVar, Optional, Any,
    NoReturn, Annotated, List, ClassVar,
    Final, MutableMapping, Literal,
    Union, get_type_hints
)

from . import normalize_type, is_subclass_soft, is_new_type, is_typed_dict_class
from .normalize_type import BaseNormType, NormTV
from .utils import is_protocol
from ..common import TypeHint

SubtypeMatch = Dict[TypeVar, TypeHint]


class SubtypeMatcher(ABC):
    @abstractmethod
    def __call__(self, sub_tp: TypeHint) -> Optional[SubtypeMatch]:
        pass

    @abstractmethod
    def is_subtype(self, sub_tp: TypeHint) -> bool:
        pass


def _norm_dict_values(dct):
    return {k: normalize_type(v) for k, v in dct.items()}


@dataclass
class MatchCtx:
    match: Dict[NormTV, BaseNormType]
    s_ctx: MutableMapping
    o_ctx: MutableMapping


# noinspection PyUnusedLocal, PyMethodMayBeStatic
class DefaultSubtypeMatcher(SubtypeMatcher):
    def __init__(self, tp: TypeHint):
        self._source_tp = normalize_type(tp)

    def __call__(self, sub_tp: TypeHint) -> Optional[SubtypeMatch]:
        norm_sub_tp = normalize_type(sub_tp)

        ctx = MatchCtx(match={}, s_ctx={}, o_ctx={})
        success = self._match(ctx, self._source_tp, norm_sub_tp)
        if success:
            return {
                k.origin: v.source
                for k, v in ctx.match.items()
            }
        return None

    def is_subtype(self, sub_tp: TypeHint) -> bool:
        return self(sub_tp) is not None

    def _match(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        old_s_ctx = copy(ctx.s_ctx)
        old_o_ctx = copy(ctx.o_ctx)

        result = self._o_match_dispatch(ctx, tp, sub_tp)

        ctx.s_ctx = old_s_ctx
        ctx.o_ctx = old_o_ctx
        return result

    # other match methods for every type

    def _o_match_dispatch(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        try:
            func = self._O_MATCH_DISPATCHING[sub_tp.origin]
        except KeyError:
            pass
        else:
            return func(self, ctx, tp, sub_tp)  # type: ignore

        return self._dispatch_match(ctx, tp, sub_tp)

    def _o_match_first_arg(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        return self._match(ctx, tp, sub_tp.args[0])

    def _o_match_union(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        return all(
            self._match(ctx, tp, sub_tp_arg)
            for sub_tp_arg in sub_tp.args
        )

    _O_MATCH_DISPATCHING = {
        Annotated: _o_match_first_arg,
        ClassVar: _o_match_first_arg,
        Final: _o_match_first_arg,
        Union: _o_match_union,
    }

    # match methods for every type

    def _match_any(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        return True

    def _match_none(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        return sub_tp.origin is None

    def _match_no_return(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        return sub_tp.origin == NoReturn

    def _match_first_arg(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        return self._match(ctx, tp.args[0], sub_tp)  # Annotated[T, ...] Final[T] ClassVar[T]

    def _match_tuple(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        if not is_subclass_soft(sub_tp.origin, tuple):
            return False

        if tp.args[-1] is ...:
            if sub_tp.args[-1] is ...:
                # Tuple[T, ...] and Tuple[K, ...]
                return self._match(
                    ctx, tp.args[0], sub_tp.args[0]
                )

            # Tuple[T, ...] and Tuple[K1, K2, ]
            return all(
                self._match(ctx, tp.args[0], other_arg)
                for other_arg in sub_tp.args
            )

        # Tuple[T1, T2, ] and Tuple[K, ...]
        if sub_tp.args[-1] is ...:
            return False

        # Tuple[T1, T2, ] and Tuple[K1, K2]
        if len(tp.args) != len(sub_tp.args):
            return False

        return self._match_all_args(ctx, tp.args, sub_tp.args)

    def _match_literal(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        if tp.origin != Literal:
            return False

        return set(sub_tp.args).issubset(set(tp.args))

    def _match_new_type(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        return tp.origin == sub_tp.origin  # exactly the same NewType object

    def _match_all_args(self, ctx: MatchCtx, tp_list: List[BaseNormType], sub_tp_list: List[BaseNormType]) -> bool:
        if len(tp_list) != len(sub_tp_list):
            return False

        return all(
            self._match(ctx, s_arg, o_arg)
            for s_arg, o_arg in zip(tp_list, sub_tp_list)
        )

    def _match_callable(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        if not is_subclass_soft(tp.origin, c_abc.Callable):
            return False

        s_call_args, s_result_type = tp.args
        o_call_args, o_result_type = sub_tp.args

        if s_call_args is ...:
            return self._match(ctx, s_result_type, o_result_type)

        if o_call_args is ...:
            return False

        return (
            self._match_all_args(ctx, o_call_args, s_call_args)  # args are contravariants
            and
            self._match(ctx, s_result_type, o_result_type)
        )

    def _match_typed_dict(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        if not is_typed_dict_class(sub_tp.origin):
            return False

        if tp.origin.__total__ != sub_tp.origin.__total__:
            return False

        source = _norm_dict_values(get_type_hints(tp.origin))
        other = _norm_dict_values(get_type_hints(sub_tp.origin))

        source_keys = set(source)
        other_keys = set(other)

        if not other_keys.issubset(source_keys):
            return False

        return all(
            self._match(ctx, source[name], other[name])
            for name in source_keys & other_keys
        )

    def _match_by_template(self, ctx: MatchCtx, tmpl: NormTV, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        if not tmpl.is_template:
            raise RuntimeError

        if tmpl.covariant:
            return self._match(ctx, tp, sub_tp)
        if tmpl.contravariant:
            return self._match_contra(ctx, tp, sub_tp)
        if tmpl.invariant:
            return (
                self._match(ctx, tp, sub_tp)
                and
                self._match_contra(ctx, tp, sub_tp)
            )

        raise RuntimeError

    def _match_contra(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        if isinstance(tp, NormTV):
            return self._match_type_var(ctx, tp, sub_tp, straight=False)

        old_s_ctx = copy(ctx.ma)
        old_o_ctx = copy(ctx.o_ctx)

        result = self._o_match_dispatch(ctx, tp, sub_tp)

        ctx.s_ctx = old_s_ctx
        ctx.o_ctx = old_o_ctx

    def _match_generic_type(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        if not is_subclass_soft(sub_tp.origin, tp.origin):
            return False

        tmpl_list: List[NormTV] = normalize_type(tp.origin).args

        if not (len(tmpl_list) == len(tp.args) == len(sub_tp.args)):
            raise RuntimeError

        return all(
            self._match_by_template(
                ctx, tmpl, tp_arg, sub_tp_arg
            )
            for tmpl, tp_arg, sub_tp_arg in zip(
                tmpl_list, tp.args, sub_tp.args
            )
        )

    def _match_type_var(self, ctx: MatchCtx, tp: NormTV, sub_tp: BaseNormType, straight: bool = True) -> bool:
        if isinstance(sub_tp, NormTV):
            if tp.origin == sub_tp.origin:
                return True

            raise ValueError(f'{type(self).__name__} does not support type var matching')

        if tp.bound is not None:
            inner_ctx = replace(ctx, match={})

            if straight:
                result = self._match(inner_ctx, tp.bound, sub_tp)
            else:
                inner_ctx.s_ctx, inner_ctx.o_ctx = inner_ctx.o_ctx, inner_ctx.s_ctx
                result = self._match(inner_ctx, sub_tp, tp.bound)

            if not result:
                return False

        if tp.constraints:
            for constraint in tp.constraints:
                inner_ctx = replace(ctx, match={})
                if self._match(inner_ctx, constraint, sub_tp):
                    break
            else:
                return False

        if tp in ctx.match:
            return ctx.match[tp] == sub_tp

        if not tp.is_template:
            ctx.match[tp] = sub_tp

        return True

    def _match_union(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        # sub_tp can not be a Union due to _o_match_union
        return any(
            self._match(ctx, tp_arg, sub_tp)
            for tp_arg in tp.args
        )

    def _match_protocol(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        if not isinstance(sub_tp.origin, type):
            return False

        if is_protocol(sub_tp.origin):
            return False

        try:
            return issubclass(sub_tp.origin, tp.origin)
        except TypeError:
            raise ValueError(f'{type(self).__name__} does not support non-runtime protocol matching')

    def _dispatch_match(self, ctx: MatchCtx, tp: BaseNormType, sub_tp: BaseNormType) -> bool:
        try:
            func = self._MATCH_DISPATCHING_SPECIAL[tp.origin]
        except KeyError:
            pass
        else:
            return func(self, ctx, tp, sub_tp)  # type: ignore

        if is_protocol(tp.origin):
            return self._match_protocol(ctx, tp, sub_tp)

        if is_typed_dict_class(tp.origin):
            return self._match_typed_dict(ctx, tp, sub_tp)

        if isinstance(tp.origin, type):
            return self._match_generic_type(ctx, tp, sub_tp)

        if isinstance(tp, NormTV):
            return self._match_type_var(ctx, tp, sub_tp)

        if is_new_type(tp.origin):
            return self._match_new_type(ctx, tp, sub_tp)

        raise ValueError(f'{type(self).__name__} сan not check subtype of {tp}')

    _MATCH_DISPATCHING_SPECIAL = {
        Any: _match_any,
        None: _match_none,
        NoReturn: _match_no_return,
        Annotated: _match_first_arg,
        Final: _match_first_arg,
        ClassVar: _match_first_arg,
        c_abc.Callable: _match_callable,
        tuple: _match_tuple,
        Literal: _match_literal,
        Union: _match_union,
    }
