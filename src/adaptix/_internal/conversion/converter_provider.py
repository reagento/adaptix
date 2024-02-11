from abc import ABC, abstractmethod
from functools import reduce
from inspect import Parameter, Signature
from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple, cast, final

from ..code_tools.compiler import BasicClosureCompiler, ClosureCompiler
from ..common import Converter, TypeHint
from ..conversion.broaching.code_generator import BroachingCodeGenerator, BroachingPlan, BuiltinBroachingCodeGenerator
from ..conversion.broaching.definitions import (
    AccessorElement,
    FuncCallArg,
    FunctionElement,
    KeywordArg,
    ParameterElement,
    PositionalArg,
)
from ..conversion.request_cls import (
    CoercerRequest,
    ConverterRequest,
    LinkingDest,
    LinkingRequest,
    LinkingResult,
    LinkingSource,
    UnlinkedOptionalPolicyRequest,
)
from ..model_tools.definitions import BaseField, DefaultValue, InputField, InputShape, NoDefault, OutputShape, ParamKind
from ..morphing.model.basic_gen import NameSanitizer, compile_closure_with_globals_capturing, fetch_code_gen_hook
from ..provider.essential import CannotProvide, Mediator, mandatory_apply_by_iterable
from ..provider.fields import base_field_to_loc_map, input_field_to_loc_map
from ..provider.request_cls import LocMap, LocStack, TypeHintLoc
from ..provider.shape_provider import InputShapeRequest, OutputShapeRequest, provide_generic_resolved_shape
from ..provider.static_provider import StaticProvider, static_provision_action
from ..utils import add_note


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
        dst_model_field = self._get_dst_field(signature.return_annotation)
        dst_shape = self._fetch_dst_shape(mediator, dst_model_field)
        src_shape = self._fetch_src_shape(mediator, source_model_field)
        broaching_plan = self._make_broaching_plan(
            mediator=mediator,
            dst_shape=dst_shape,
            src_shape=src_shape,
            owner_linking_src=LinkingSource(source_model_field),
            owner_linking_dst=LinkingDest(dst_model_field),
            extra_params=tuple(map(LinkingSource, extra_params)),
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
            signature=request.signature,
            closure_name=closure_name,
            stub_function=request.stub_function,
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
        stub_function_name = getattr(request.stub_function, '__name__', None)
        if stub_function_name is not None:
            return stub_function_name
        src = next(iter(request.signature.parameters.values()))
        dst = self._get_type_from_annotation(request.signature.return_annotation)
        return self._name_sanitizer.sanitize(f'convert_{src}_to_{dst}')

    def _get_file_name(self, request: ConverterRequest) -> str:
        if request.function_name is not None:
            return request.function_name
        stub_function_name = getattr(request.stub_function, '__name__', None)
        if stub_function_name is not None:
            return stub_function_name
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

    def _get_dst_field(self, return_annotation: Any) -> InputField:
        return InputField(
            id='__return__',
            type=self._get_type_from_annotation(return_annotation),
            metadata={},
            default=NoDefault(),
            original=None,
            is_required=True,
        )

    def _fetch_dst_shape(self, mediator: Mediator, model_dst_field: InputField) -> InputShape:
        return provide_generic_resolved_shape(
            mediator,
            InputShapeRequest(loc_stack=LocStack(input_field_to_loc_map(model_dst_field))),
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

    def _fetch_linkings(
        self,
        mediator: Mediator,
        dst_shape: InputShape,
        src_shape: OutputShape,
        owner_linking_src: LinkingSource,
        owner_linking_dst: LinkingDest,
        extra_params: Sequence[LinkingSource],
    ) -> Iterable[Tuple[InputField, Optional[LinkingResult]]]:
        model_linking_sources = tuple(
            owner_linking_src.append_with(src_field)
            for src_field in src_shape.fields
        )
        sources = (model_linking_sources, *extra_params)

        def fetch_field_linking(dst_field: InputField) -> Tuple[InputField, Optional[LinkingResult]]:
            destination = owner_linking_dst.append_with(dst_field)
            try:
                linking = mediator.provide(
                    LinkingRequest(
                        sources=sources,  # type: ignore[arg-type]
                        destination=destination,
                    )
                )
            except CannotProvide as e:
                if dst_field.is_required:
                    add_note(e, 'Note: This is a required filed, so it must take value')
                    raise

                policy = mediator.mandatory_provide(
                    UnlinkedOptionalPolicyRequest(loc_stack=destination.to_loc_stack())
                )
                if policy.is_allowed:
                    return dst_field, None
                add_note(
                    e,
                    'Note: Current policy forbids unlinked optional fields,'
                    ' so you need to link it to another field'
                    ' or explicitly confirm the desire to skipping using `allow_unlinked_optional`'
                )
                raise
            return dst_field, linking

        return mandatory_apply_by_iterable(
            fetch_field_linking,
            zip(dst_shape.fields),
            lambda: 'Linkings for some fields are not found',
        )

    def _get_nested_models_sub_plan(
        self,
        mediator: Mediator,
        linking_src: LinkingSource,
        linking_dst: LinkingDest,
        extra_params: Sequence[LinkingSource],
    ) -> Optional[BroachingPlan]:
        try:
            dst_shape = provide_generic_resolved_shape(
                mediator,
                InputShapeRequest(loc_stack=linking_dst.to_loc_stack())
            )
            src_shape = provide_generic_resolved_shape(
                mediator,
                OutputShapeRequest(loc_stack=linking_src.to_loc_stack())
            )
        except CannotProvide:
            return None

        return self._make_broaching_plan(
            mediator=mediator,
            dst_shape=dst_shape,
            src_shape=src_shape,
            extra_params=extra_params,
            owner_linking_src=linking_src,
            owner_linking_dst=linking_dst,
        )

    def _linking_source_to_plan(self, linking_src: LinkingSource) -> BroachingPlan:
        return reduce(
            lambda plan, item: (
                AccessorElement(
                    target=plan,
                    accessor=item.accessor,
                )
            ),
            linking_src.tail,
            cast(BroachingPlan, ParameterElement(linking_src.head.id)),
        )

    def _get_coercer_sub_plan(
        self,
        mediator: Mediator,
        linking_src: LinkingSource,
        linking_dst: LinkingDest,
    ) -> BroachingPlan:
        coercer = mediator.provide(
            CoercerRequest(
                src=linking_src,
                dst=linking_dst,
            )
        )
        return FunctionElement(
            func=coercer,
            args=(
                PositionalArg(
                    self._linking_source_to_plan(linking_src)
                ),
            ),
        )

    def _generate_field_to_sub_plan(
        self,
        mediator: Mediator,
        extra_params: Sequence[LinkingSource],
        field_linkings: Iterable[Tuple[InputField, LinkingResult]],
        owner_linking_dst: LinkingDest,
    ) -> Mapping[InputField, BroachingPlan]:
        def generate_sub_plan(input_field: InputField, linking: LinkingResult):
            linking_dst = owner_linking_dst.append_with(input_field)
            try:
                return self._get_coercer_sub_plan(
                    mediator=mediator,
                    linking_src=linking.source,
                    linking_dst=linking_dst,
                )
            except CannotProvide as e:
                result = self._get_nested_models_sub_plan(
                    mediator=mediator,
                    linking_src=linking.source,
                    linking_dst=linking_dst,
                    extra_params=extra_params,
                )
                if result is not None:
                    return result
                raise e

        coercers = mandatory_apply_by_iterable(
            generate_sub_plan,
            field_linkings,
            lambda: 'Coercers for some linkings are not found',
        )
        return {
            dst_field: coercer
            for (dst_field, linking), coercer in zip(field_linkings, coercers)
        }

    def _make_broaching_plan(
        self,
        mediator: Mediator,
        dst_shape: InputShape,
        src_shape: OutputShape,
        extra_params: Sequence[LinkingSource],
        owner_linking_src: LinkingSource,
        owner_linking_dst: LinkingDest,
    ) -> BroachingPlan:
        field_linkings = self._fetch_linkings(
            mediator=mediator,
            dst_shape=dst_shape,
            src_shape=src_shape,
            extra_params=extra_params,
            owner_linking_src=owner_linking_src,
            owner_linking_dst=owner_linking_dst,
        )
        field_to_sub_plan = self._generate_field_to_sub_plan(
            mediator=mediator,
            field_linkings=[
                (dst_field, linking)
                for dst_field, linking in field_linkings
                if linking is not None
            ],
            extra_params=extra_params,
            owner_linking_dst=owner_linking_dst,
        )
        return self._make_constructor_call(
            dst_shape=dst_shape,
            field_to_linking=dict(field_linkings),
            field_to_sub_plan=field_to_sub_plan,
        )

    def _make_constructor_call(
        self,
        dst_shape: InputShape,
        field_to_linking: Mapping[InputField, Optional[LinkingResult]],
        field_to_sub_plan: Mapping[InputField, BroachingPlan],
    ) -> BroachingPlan:
        args: List[FuncCallArg[BroachingPlan]] = []
        has_skipped_params = False
        for param in dst_shape.params:
            field = dst_shape.fields_dict[param.field_id]

            if field_to_linking[field] is None:
                has_skipped_params = True
                continue

            sub_plan = field_to_sub_plan[field]
            if param.kind == ParamKind.KW_ONLY or has_skipped_params:
                args.append(KeywordArg(param.name, sub_plan))
            elif param.kind == ParamKind.POS_ONLY and has_skipped_params:
                raise CannotProvide(
                    'Can not generate consistent constructor call,'
                    ' positional-only parameter is skipped',
                    is_demonstrative=True,
                )
            else:
                args.append(PositionalArg(sub_plan))

        return FunctionElement(
            func=dst_shape.constructor,
            args=tuple(args),
        )
