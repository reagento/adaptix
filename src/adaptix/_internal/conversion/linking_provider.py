import itertools
from typing import AbstractSet, Callable, Iterable, Optional, Union

from ..common import Coercer, OneArgCoercer
from ..model_tools.definitions import DefaultFactory, DefaultValue, InputField, InputShape
from ..model_tools.introspection.callable import get_callable_shape
from ..provider.essential import CannotProvide, Mediator, Provider
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
    def __init__(
        self,
        func: Callable,
        dst_lsc: LocStackChecker,
        pass_model: AbstractSet[str],
        pass_params: AbstractSet[str],
    ):
        self._func = func
        self._dst_lsc = dst_lsc
        self._pass_model = pass_model
        self._pass_params = pass_params
        self._input_shape = self._get_input_shape()
        self._retort = self._build_retort()
        self._validate()

    def _get_input_shape(self) -> InputShape:
        return get_callable_shape(self._func).input

    def _validate(self) -> None:
        duplicated = self._pass_params & self._pass_model
        if duplicated:
            raise ValueError(f"Markers {duplicated} presented in `pass_params` and `pass_model`")

        all_params = self._pass_params | self._pass_model

        non_identifier_params = [param for param in all_params if not param.isidentifier()]
        if non_identifier_params:
            raise ValueError("All markers must be a valid python identifier to exactly match parameter")

        wild_params = {field.id for field in self._input_shape.fields} - all_params
        if wild_params:
            raise ValueError(f"Markers {duplicated} does not match with any function parameters")

    def _build_retort(self) -> OperatingRetort:
        return OperatingRetort(
            recipe=[
                self._get_field_provider(field)
                for field in self._input_shape.fields
            ],
        )

    def _get_field_provider(self, field: InputField) -> Provider:
        if field.id in self._pass_model:
            return ModelLinkingProvider(dst_lsc=create_loc_stack_checker(field.id))
        if field.id in self._pass_params:
            return MatchingLinkingProvider(
                src_lsc=FromCtxParam(field.id),
                dst_lsc=create_loc_stack_checker(field.id),
                coercer=None,
            )
        return MatchingLinkingProvider(
            src_lsc=create_loc_stack_checker(field.id),
            dst_lsc=create_loc_stack_checker(field.id),
            coercer=None,
        )

    def _get_linking(self, mediator: Mediator, request: LinkingRequest, input_field: InputField) -> LinkingResult:
        return self._retort.apply_provider(
            mediator,
            LinkingRequest(
                sources=request.sources,
                context=request.context,
                destination=request.destination.append_with(input_field_to_loc(input_field)),
            ),
        )

    def _provide_linking(self, mediator: Mediator, request: LinkingRequest) -> LinkingResult:
        if self._dst_lsc.check_loc_stack(mediator, request.destination):
            param_specs = tuple(
                FunctionLinking.ParamSpec(
                    field=self._input_shape.fields_dict[param.field_id],
                    linking=self._get_linking(mediator, request, self._input_shape.fields_dict[param.field_id]),
                    param_kind=param.kind,
                )
                for param in self._input_shape.params
            )
            return LinkingResult(linking=FunctionLinking(func=self._func, param_specs=param_specs))
        raise CannotProvide
