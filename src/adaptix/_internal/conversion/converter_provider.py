from abc import ABC, abstractmethod
from functools import reduce
from inspect import Parameter, Signature
from typing import Any, Iterable, Optional, Sequence, cast, final

from ..code_tools.compiler import BasicClosureCompiler, ClosureCompiler
from ..common import Converter, TypeHint
from ..conversion.broaching.code_generator import BroachingCodeGenerator, BroachingPlan, BuiltinBroachingCodeGenerator
from ..conversion.broaching.definitions import (
    AccessorElement,
    FunctionElement,
    KeywordArg,
    ParameterElement,
    PositionalArg,
)
from ..conversion.request_cls import (
    BindingDest,
    BindingRequest,
    BindingResult,
    BindingSource,
    CoercerRequest,
    ConverterRequest,
)
from ..model_tools.definitions import BaseField, DefaultValue, InputField, InputShape, NoDefault, OutputShape, ParamKind
from ..morphing.model.basic_gen import NameSanitizer, compile_closure_with_globals_capturing, fetch_code_gen_hook
from ..provider.essential import CannotProvide, Mediator, mandatory_apply_by_iterable
from ..provider.fields import base_field_to_loc_map, input_field_to_loc_map
from ..provider.request_cls import LocMap, LocStack, TypeHintLoc
from ..provider.shape_provider import InputShapeRequest, OutputShapeRequest, provide_generic_resolved_shape
from ..provider.static_provider import StaticProvider, static_provision_action


class ConverterProvider(StaticProvider, ABC):
    @final
    @static_provision_action
    def _outer_provide_converter(self, mediator: Mediator, request: ConverterRequest):
        return self._provide_converter(mediator, request)

    @abstractmethod
    def _provide_converter(self, mediator: Mediator, request: ConverterRequest) -> Converter:
        ...


class BuiltinConverterProvider(ConverterProvider):
    def __init__(self, *, name_sanitizer: NameSanitizer = NameSanitizer()):
        self._name_sanitizer = name_sanitizer

    def _provide_converter(self, mediator: Mediator, request: ConverterRequest) -> Converter:
        signature = request.signature
        if len(signature.parameters.values()) == 0:
            raise CannotProvide(
                message='At least one parameter is required',
                is_demonstrative=True,
            )
        if any(
            param.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)
            for param in signature.parameters.values()
        ):
            raise CannotProvide(
                message='Parameters specified by *args and **kwargs are not supported',
                is_demonstrative=True,
            )

        source_model_field, *extra_params = map(self._param_to_base_field, signature.parameters.values())
        dst_shape = self._fetch_dst_shape(mediator, signature.return_annotation)
        src_shape = self._fetch_src_shape(mediator, source_model_field)
        broaching_plan = self._make_broaching_plan(
            mediator=mediator,
            dst_shape=dst_shape,
            src_shape=src_shape,
            owner_binding_src=BindingSource(source_model_field),
            owner_binding_dst=BindingDest(),
            extra_params=tuple(map(BindingSource, extra_params)),
        )
        return self._make_converter(mediator, request, broaching_plan, signature)

    def _make_converter(
        self,
        mediator: Mediator,
        request: ConverterRequest,
        broaching_plan: BroachingPlan,
        signature: Signature,
    ):
        code_gen = self._create_broaching_code_gen(broaching_plan)
        closure_name = self._get_closure_name(request)
        dumper_code, dumper_namespace = code_gen.produce_code(
            closure_name=closure_name,
            signature=request.signature,
        )
        code_gen_loc_stack = LocStack(LocMap(TypeHintLoc(self._get_type_from_annotation(signature.return_annotation))))
        return compile_closure_with_globals_capturing(
            compiler=self._get_compiler(),
            code_gen_hook=fetch_code_gen_hook(mediator, code_gen_loc_stack),
            namespace=dumper_namespace,
            closure_code=dumper_code,
            closure_name=closure_name,
            file_name=self._get_file_name(request),
        )

    def _get_closure_name(self, request: ConverterRequest) -> str:
        if request.function_name is not None:
            return request.function_name
        src = next(iter(request.signature.parameters.values()))
        dst = self._get_type_from_annotation(request.signature.return_annotation)
        return self._name_sanitizer.sanitize(f'convert_{src}_to_{dst}')

    def _get_file_name(self, request: ConverterRequest) -> str:
        if request.function_name is not None:
            return request.function_name
        src = next(iter(request.signature.parameters.values()))
        dst = self._get_type_from_annotation(request.signature.return_annotation)
        return f'convert_{src}_to_{dst}'

    def _get_type_from_annotation(self, annotation: Any) -> TypeHint:
        return Any if annotation == Signature.empty else annotation

    def _param_to_base_field(self, parameter: Parameter) -> BaseField:
        return BaseField(
            id=parameter.name,
            type=self._get_type_from_annotation(parameter.annotation),
            default=NoDefault() if parameter.default == Signature.empty else DefaultValue(parameter.default),
            metadata={},
            original=None,
        )

    def _fetch_dst_shape(self, mediator: Mediator, return_annotation: Any) -> InputShape:
        dst_loc_map = input_field_to_loc_map(
            InputField(
                id='__return__',
                type=self._get_type_from_annotation(return_annotation),
                metadata={},
                default=NoDefault(),
                original=None,
                is_required=True,
            )
        )
        return provide_generic_resolved_shape(
            mediator,
            InputShapeRequest(loc_stack=LocStack(dst_loc_map)),
        )

    def _fetch_src_shape(self, mediator: Mediator, source_model_field: BaseField) -> OutputShape:
        src_loc_map = base_field_to_loc_map(source_model_field)
        return provide_generic_resolved_shape(
            mediator,
            OutputShapeRequest(loc_stack=LocStack(src_loc_map)),
        )

    def _get_compiler(self) -> ClosureCompiler:
        return BasicClosureCompiler()

    def _create_broaching_code_gen(self, plan: BroachingPlan) -> BroachingCodeGenerator:
        return BuiltinBroachingCodeGenerator(plan=plan)

    def _fetch_bindings(
        self,
        mediator: Mediator,
        dst_shape: InputShape,
        src_shape: OutputShape,
        owner_binding_src: BindingSource,
        owner_binding_dst: BindingDest,
        extra_params: Sequence[BindingSource],
    ) -> Iterable[BindingResult]:
        model_binding_sources = tuple(
            owner_binding_src.append_with(src_field)
            for src_field in src_shape.fields
        )
        bindings = mediator.mandatory_provide_by_iterable(
            [
                BindingRequest(
                    sources=(
                        model_binding_sources,
                        *extra_params,
                    ),
                    destination=owner_binding_dst.append_with(dst_field),
                )
                for dst_field in dst_shape.fields
            ]
        )
        return bindings

    def _get_nested_models_sub_plan(
        self,
        mediator: Mediator,
        binding_src: BindingSource,
        binding_dst: BindingDest,
        extra_params: Sequence[BindingSource],
    ) -> Optional[BroachingPlan]:
        try:
            dst_shape = provide_generic_resolved_shape(
                mediator,
                InputShapeRequest(loc_stack=binding_dst.to_loc_stack())
            )
            src_shape = provide_generic_resolved_shape(
                mediator,
                OutputShapeRequest(loc_stack=binding_src.to_loc_stack())
            )
        except CannotProvide:
            return None

        return self._make_broaching_plan(
            mediator=mediator,
            dst_shape=dst_shape,
            src_shape=src_shape,
            extra_params=extra_params,
            owner_binding_src=binding_src,
            owner_binding_dst=binding_dst,
        )

    def _binding_source_to_plan(self, binding_src: BindingSource) -> BroachingPlan:
        return reduce(
            lambda plan, item: (
                AccessorElement(
                    target=plan,
                    accessor=item.accessor,
                )
            ),
            binding_src.tail,
            cast(BroachingPlan, ParameterElement(binding_src.head.id)),
        )

    def _get_coercer_sub_plan(
        self,
        mediator: Mediator,
        binding_src: BindingSource,
        binding_dst: BindingDest,
    ) -> BroachingPlan:
        coercer = mediator.provide(
            CoercerRequest(
                src=binding_src,
                dst=binding_dst,
            )
        )
        return FunctionElement(
            func=coercer,
            args=(
                PositionalArg(
                    self._binding_source_to_plan(binding_src)
                ),
            ),
        )

    def _generate_binding_sub_plans(
        self,
        mediator: Mediator,
        dst_shape: InputShape,
        extra_params: Sequence[BindingSource],
        bindings: Iterable[BindingResult],
        owner_binding_dst: BindingDest,
    ) -> Iterable[BroachingPlan]:
        def generate_sub_plan(input_field: InputField, binding: BindingResult):
            binding_dst = owner_binding_dst.append_with(input_field)
            result = self._get_nested_models_sub_plan(
                mediator=mediator,
                binding_src=binding.source,
                binding_dst=binding_dst,
                extra_params=extra_params,
            )
            if result is not None:
                return result

            return self._get_coercer_sub_plan(
                mediator=mediator,
                binding_src=binding.source,
                binding_dst=binding_dst,
            )

        return mandatory_apply_by_iterable(
            generate_sub_plan,
            zip(dst_shape.fields, bindings),
        )

    def _make_broaching_plan(
        self,
        mediator: Mediator,
        dst_shape: InputShape,
        src_shape: OutputShape,
        extra_params: Sequence[BindingSource],
        owner_binding_src: BindingSource,
        owner_binding_dst: BindingDest,
    ) -> BroachingPlan:
        bindings = self._fetch_bindings(
            mediator=mediator,
            dst_shape=dst_shape,
            src_shape=src_shape,
            extra_params=extra_params,
            owner_binding_src=owner_binding_src,
            owner_binding_dst=owner_binding_dst,
        )
        sub_plans = self._generate_binding_sub_plans(
            mediator=mediator,
            dst_shape=dst_shape,
            bindings=bindings,
            extra_params=extra_params,
            owner_binding_dst=owner_binding_dst,
        )
        return FunctionElement(
            func=dst_shape.constructor,
            args=tuple(
                KeywordArg(param.name, sub_plan)
                if param.kind == ParamKind.KW_ONLY else
                PositionalArg(sub_plan)
                for param, binding, sub_plan in zip(dst_shape.params, bindings, sub_plans)
            ),
        )
