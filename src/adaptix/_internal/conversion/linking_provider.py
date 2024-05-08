import itertools
from typing import Callable, Iterable, Optional, Union

from ..common import Coercer, OneArgCoercer
from ..model_tools.definitions import DefaultFactory, DefaultValue, InputField, InputShape, Param, ParamKind
from ..model_tools.introspection.callable import get_callable_shape
from ..provider.essential import CannotProvide, Mediator, Provider, mandatory_apply_by_iterable
from ..provider.fields import input_field_to_loc
from ..provider.loc_stack_filtering import LocStackChecker, create_loc_stack_checker
from ..provider.location import FieldLoc
from ..retort.operating_retort import OperatingRetort
from .provider_template import LinkingProvider
from .request_cls import (
    ConstantLinking,
    FieldLinking,
    FunctionLinking,
    LinkingRequest,
    LinkingResult,
    LinkingSource,
    ModelLinking,
)
from .request_filtering import FromCtxParam


class DefaultLinkingProvider(LinkingProvider):
    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        target_field_id = request.destination.last.cast(FieldLoc).field_id

        for source in self._iterate_sources(request):
            if source.last.cast(FieldLoc).field_id == target_field_id:
                return LinkingResult(
                    linking=FieldLinking(source=source, coercer=None),
                )
        raise CannotProvide

    def _iterate_sources(self, request: LinkingRequest) -> Iterable[LinkingSource]:
        if len(request.destination) == 2:  # noqa: PLR2004
            yield from reversed(request.context.loc_stacks)
        yield from request.sources


class MatchingLinkingProvider(LinkingProvider):
    def __init__(self, src_lsc: LocStackChecker, dst_lsc: LocStackChecker, coercer: Optional[OneArgCoercer]):
        self._src_lsc = src_lsc
        self._dst_lsc = dst_lsc
        self._one_arg_coercer = coercer

    def _get_coercer(self) -> Optional[Coercer]:
        one_arg_coercer = self._one_arg_coercer
        if one_arg_coercer is None:
            return None
        return lambda x, ctx: one_arg_coercer(x)

    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        if not self._dst_lsc.check_loc_stack(mediator, request.destination):
            raise CannotProvide

        for source in itertools.chain(request.sources, reversed(request.context.loc_stacks)):
            if self._src_lsc.check_loc_stack(mediator, source):
                return LinkingResult(linking=FieldLinking(source=source, coercer=self._get_coercer()))
        raise CannotProvide


class ConstantLinkingProvider(LinkingProvider):
    def __init__(self, dst_lsc: LocStackChecker, default: Union[DefaultValue, DefaultFactory]):
        self._dst_lsc = dst_lsc
        self._default = default

    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        if self._dst_lsc.check_loc_stack(mediator, request.destination):
            return LinkingResult(linking=ConstantLinking(self._default))
        raise CannotProvide


class ModelLinkingProvider(LinkingProvider):
    def __init__(self, dst_lsc: LocStackChecker):
        self._dst_lsc = dst_lsc

    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        if self._dst_lsc.check_loc_stack(mediator, request.destination):
            return LinkingResult(linking=ModelLinking())
        raise CannotProvide


class FunctionLinkingProvider(LinkingProvider):
    def __init__(self, func: Callable, dst_lsc: LocStackChecker):
        self._func = func
        self._dst_lsc = dst_lsc
        self._input_shape = self._get_input_shape()
        self._retort = self._build_retort()

    def _get_input_shape(self) -> InputShape:
        return get_callable_shape(self._func).input

    def _build_retort(self) -> OperatingRetort:
        return OperatingRetort(
            recipe=[
                self._get_field_provider(field, param, idx)
                for idx, (field, param) in enumerate(zip(self._input_shape.fields, self._input_shape.params))
            ],
        )

    def _get_field_provider(self, field: InputField, param: Param, idx: int) -> Provider:
        if param.kind == ParamKind.KW_ONLY:
            return MatchingLinkingProvider(
                src_lsc=create_loc_stack_checker(field.id),
                dst_lsc=create_loc_stack_checker(field.id),
                coercer=None,
            )
        if idx == 0:
            return ModelLinkingProvider(dst_lsc=create_loc_stack_checker(field.id))
        return MatchingLinkingProvider(
            src_lsc=FromCtxParam(field.id),
            dst_lsc=create_loc_stack_checker(field.id),
            coercer=None,
        )

    def _get_linking(self, mediator: Mediator, request: LinkingRequest, input_field: InputField) -> LinkingResult:
        dest = request.destination.append_with(input_field_to_loc(input_field).complement_with_func(self._func))
        return self._retort.apply_provider(
            mediator,
            LinkingRequest(
                sources=request.sources,
                context=request.context,
                destination=dest,
            ),
        )

    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        if not self._dst_lsc.check_loc_stack(mediator, request.destination):
            raise CannotProvide

        param_specs = mandatory_apply_by_iterable(
            lambda field, param: FunctionLinking.ParamSpec(
                field=field,
                linking=self._get_linking(mediator, request, field),
                param_kind=param.kind,
            ),
            zip(self._input_shape.fields, self._input_shape.params),
            lambda: "Cannot create linking for function. Linkings for some parameters are not found",
        )
        return LinkingResult(
            linking=FunctionLinking(func=self._func, param_specs=tuple(param_specs)),
        )
