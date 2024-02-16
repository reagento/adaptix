from abc import ABC, abstractmethod
from typing import Any

from ..common import Coercer
from ..provider.essential import CannotProvide, Mediator
from ..provider.loc_stack_filtering import LocStackChecker
from ..provider.request_cls import try_normalize_type
from ..provider.static_provider import StaticProvider, static_provision_action
from ..special_cases_optimization import as_is_stub
from ..type_tools import is_generic, is_subclass_soft, strip_tags
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


class SubclassCoercerProvider(CoercerProvider):
    def _provide_coercer(self, mediator: Mediator, request: CoercerRequest) -> Coercer:
        src_tp = request.src[-1].type
        dst_tp = request.dst[-1].type

        if is_generic(src_tp) or is_generic(dst_tp):
            raise CannotProvide

        norm_src = try_normalize_type(src_tp)
        norm_dst = try_normalize_type(dst_tp)
        stripped_src = strip_tags(norm_src)
        stripped_dst = strip_tags(norm_dst)
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
