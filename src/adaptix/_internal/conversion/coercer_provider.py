from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Any, Union

from ..common import Coercer
from ..provider.essential import CannotProvide, Mediator
from ..provider.loc_stack_filtering import LocStackChecker
from ..provider.request_cls import try_normalize_type
from ..provider.static_provider import StaticProvider, static_provision_action
from ..special_cases_optimization import as_is_stub
from ..type_tools import BaseNormType, is_generic, is_parametrized, is_subclass_soft, strip_tags
from .request_cls import CoercerRequest


class CoercerProvider(StaticProvider, ABC):
    @static_provision_action
    @abstractmethod
    def _provide_coercer(self, mediator: Mediator, request: CoercerRequest) -> Coercer:
        ...


class SameTypeCoercerProvider(CoercerProvider):
    def _provide_coercer(self, mediator: Mediator, request: CoercerRequest) -> Coercer:
        src_tp = request.src[-1].type
        dst_tp = request.dst[-1].type

        if src_tp == dst_tp:
            return as_is_stub

        norm_src = try_normalize_type(src_tp)
        norm_dst = try_normalize_type(dst_tp)
        if strip_tags(norm_src) == strip_tags(norm_dst):
            return as_is_stub
        raise CannotProvide


class DstAnyCoercerProvider(CoercerProvider):
    def _provide_coercer(self, mediator: Mediator, request: CoercerRequest) -> Coercer:
        dst_tp = request.dst[-1].type
        norm_dst = strip_tags(try_normalize_type(dst_tp))
        if norm_dst.origin == Any:
            return as_is_stub
        raise CannotProvide


class StrippedTypeCoercerProvider(CoercerProvider, ABC):
    def _provide_coercer(self, mediator: Mediator, request: CoercerRequest) -> Coercer:
        src_tp = request.src[-1].type
        dst_tp = request.dst[-1].type
        norm_src = try_normalize_type(src_tp)
        norm_dst = try_normalize_type(dst_tp)
        stripped_src = strip_tags(norm_src)
        stripped_dst = strip_tags(norm_dst)
        return self._provide_coercer_stripped_types(mediator, request, stripped_src, stripped_dst)

    @abstractmethod
    def _provide_coercer_stripped_types(
        self,
        mediator: Mediator,
        request: CoercerRequest,
        stripped_src: BaseNormType,
        stripped_dst: BaseNormType,
    ) -> Coercer:
        ...


class SubclassCoercerProvider(StrippedTypeCoercerProvider):
    def _provide_coercer_stripped_types(
        self,
        mediator: Mediator,
        request: CoercerRequest,
        stripped_src: BaseNormType,
        stripped_dst: BaseNormType,
    ) -> Coercer:
        if (
            is_generic(stripped_src.source)
            or is_parametrized(stripped_src.source)
            or is_generic(stripped_dst.source)
            or is_parametrized(stripped_dst.source)
        ):
            raise CannotProvide
        if is_subclass_soft(stripped_src.origin, stripped_dst.origin):
            return as_is_stub
        raise CannotProvide


class MatchingCoercerProvider(CoercerProvider):
    def __init__(self, src_lsc: LocStackChecker, dst_lsc: LocStackChecker, coercer: Coercer):
        self._src_lsc = src_lsc
        self._dst_lsc = dst_lsc
        self._coercer = coercer

    def _provide_coercer(self, mediator: Mediator, request: CoercerRequest) -> Coercer:
        if (
            self._src_lsc.check_loc_stack(mediator, request.src.to_loc_stack())
            and self._dst_lsc.check_loc_stack(mediator, request.dst.to_loc_stack())
        ):
            return self._coercer
        raise CannotProvide


class UnionSubcaseCoercerProvider(StrippedTypeCoercerProvider):
    def _provide_coercer_stripped_types(
        self,
        mediator: Mediator,
        request: CoercerRequest,
        stripped_src: BaseNormType,
        stripped_dst: BaseNormType,
    ) -> Coercer:
        if stripped_dst.origin != Union:
            raise CannotProvide

        if stripped_src.origin == Union:
            src_args_set = set(map(strip_tags, stripped_src.args))
            dst_args_set = set(map(strip_tags, stripped_dst.args))
            if src_args_set.issubset(dst_args_set):
                return as_is_stub
        elif stripped_src.origin in [strip_tags(arg).origin for arg in stripped_dst.args]:
            return as_is_stub
        raise CannotProvide


class OptionalCoercerProvider(StrippedTypeCoercerProvider):
    def _provide_coercer_stripped_types(
        self,
        mediator: Mediator,
        request: CoercerRequest,
        stripped_src: BaseNormType,
        stripped_dst: BaseNormType,
    ) -> Coercer:
        if not (self._is_optional(stripped_dst) and self._is_optional(stripped_src)):
            raise CannotProvide

        not_none_src = self._get_not_none(stripped_src)
        not_none_dst = self._get_not_none(stripped_dst)
        not_none_request = replace(
            request,
            src=request.src.replace_last(replace(request.src.last, type=not_none_src)),
            dst=request.dst.replace_last(replace(request.dst.last, type=not_none_dst)),
        )
        not_none_coercer = mediator.delegating_provide(not_none_request)

        def optional_coercer(data):
            if data is None:
                return None
            return not_none_coercer(data)

        return optional_coercer

    def _is_optional(self, norm: BaseNormType) -> bool:
        return norm.origin == Union and None in [case.origin for case in norm.args]

    def _get_not_none(self, norm: BaseNormType) -> BaseNormType:
        return next(case.origin for case in norm.args if case.origin is not None)
