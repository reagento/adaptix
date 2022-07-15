from typing import Dict

from ...code_tools import BasicClosureCompiler, BuiltinContextNamespace
from ...common import Parser
from ...provider.essential import CannotProvide, Mediator
from ...provider.model.definitions import (
    InputCreationGen,
    InputCreationImage,
    InputCreationImageRequest,
    InputExtractionGen,
    InputExtractionImage,
    InputExtractionImageRequest,
    InputFigure,
    InputFigureRequest,
    VarBinder
)
from ...provider.model.input_extraction_gen import BuiltinInputExtractionGen
from ...provider.provider_template import ParserProvider
from ...provider.request_cls import ParserFieldRequest, ParserRequest
from ...provider.static_provider import StaticProvider, static_provision_action
from .basic_gen import (
    CodeGenHook,
    CodeGenHookRequest,
    DirectFieldsCollectorMixin,
    NameSanitizer,
    compile_closure_with_globals_capturing,
    strip_figure,
    stub_code_gen_hook
)
from .crown_definitions import (
    ExtraCollect,
    InpCrown,
    InpDictCrown,
    InpFieldCrown,
    InpListCrown,
    InpNoneCrown,
    InputNameMapping,
    InputNameMappingRequest
)
from .input_creation_gen import BuiltinInputCreationGen


class BuiltinInputExtractionImageProvider(StaticProvider, DirectFieldsCollectorMixin):
    @static_provision_action
    def _provide_extraction_image(
        self, mediator: Mediator, request: InputExtractionImageRequest,
    ) -> InputExtractionImage:
        name_mapping = mediator.provide(
            InputNameMappingRequest(
                type=request.initial_request.type,
                figure=request.figure,
            )
        )

        extraction_gen = self._create_extraction_gen(request, name_mapping)

        if request.figure.extra is None and self._has_collect_policy(name_mapping.crown):
            raise CannotProvide(
                "Cannot create parser that collect extra data"
                " if InputFigure does not take extra data",
                is_important=True,
            )

        used_direct_fields = self._collect_used_direct_fields(name_mapping.crown)
        skipped_direct_fields = [
            field.name for field in request.figure.fields
            if field.name not in used_direct_fields
        ]

        return InputExtractionImage(
            extraction_gen=extraction_gen,
            skipped_fields=skipped_direct_fields + list(name_mapping.skipped_extra_targets),
        )

    def _create_extraction_gen(
        self,
        request: InputExtractionImageRequest,
        name_mapping: InputNameMapping,
    ) -> InputExtractionGen:
        return BuiltinInputExtractionGen(
            figure=request.figure,
            crown=name_mapping.crown,
            debug_path=request.initial_request.debug_path,
            strict_coercion=request.initial_request.strict_coercion,
        )

    def _has_collect_policy(self, crown: InpCrown) -> bool:
        if isinstance(crown, InpDictCrown):
            return crown.extra == ExtraCollect() or any(
                self._has_collect_policy(sub_crown)
                for sub_crown in crown.map.values()
            )
        if isinstance(crown, InpListCrown):
            return any(
                self._has_collect_policy(sub_crown)
                for sub_crown in crown.map
            )
        if isinstance(crown, (InpFieldCrown, InpNoneCrown)):
            return False
        raise TypeError


class BuiltinInputCreationImageProvider(StaticProvider):
    @static_provision_action
    def _provide_extraction_image(self, mediator: Mediator, request: InputCreationImageRequest) -> InputCreationImage:
        return InputCreationImage(
            creation_gen=BuiltinInputCreationGen(
                figure=request.figure,
            )
        )


class FieldsParserProvider(ParserProvider):
    def __init__(self, name_sanitizer: NameSanitizer):
        self._name_sanitizer = name_sanitizer

    def _process_figure(self, figure: InputFigure, extraction_image: InputExtractionImage) -> InputFigure:
        skipped_required_fields = [
            field.name
            for field in figure.fields
            if field.is_required and field.name in extraction_image.skipped_fields
        ]

        if skipped_required_fields:
            raise ValueError(
                f"Required fields {skipped_required_fields} are skipped"
            )

        return strip_figure(figure, extraction_image)

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        figure: InputFigure = mediator.provide(
            InputFigureRequest(type=request.type)
        )

        extraction_image = mediator.provide(
            InputExtractionImageRequest(
                figure=figure,
                initial_request=request,
            )
        )

        processed_figure = self._process_figure(figure, extraction_image)

        creation_image = mediator.provide(
            InputCreationImageRequest(
                figure=processed_figure,
                initial_request=request,
            )
        )

        try:
            code_gen_hook = mediator.provide(CodeGenHookRequest(initial_request=request))
        except CannotProvide:
            code_gen_hook = stub_code_gen_hook

        field_parsers = {
            field.name: mediator.provide(
                ParserFieldRequest(
                    type=field.type,
                    strict_coercion=request.strict_coercion,
                    debug_path=request.debug_path,
                    default=field.default,
                    is_required=field.is_required,
                    metadata=field.metadata,
                    name=field.name,
                    param_kind=field.param_kind,
                )
            )
            for field in processed_figure.fields
        }

        return self._make_parser(
            request=request,
            creation_gen=creation_image.creation_gen,
            extraction_gen=extraction_image.extraction_gen,
            fields_parsers=field_parsers,
            code_gen_hook=code_gen_hook,
        )

    def _get_closure_name(self, request: ParserRequest) -> str:
        tp = request.type
        if isinstance(tp, type):
            name = tp.__name__
        else:
            name = str(tp)

        s_name = self._name_sanitizer.sanitize(name)
        if s_name != "":
            s_name = "_" + s_name
        return "model_parser" + s_name

    def _get_file_name(self, request: ParserRequest) -> str:
        return self._get_closure_name(request)

    def _get_compiler(self):
        return BasicClosureCompiler()

    def _get_binder(self):
        return VarBinder()

    def _make_parser(
        self,
        request: ParserRequest,
        fields_parsers: Dict[str, Parser],
        creation_gen: InputCreationGen,
        extraction_gen: InputExtractionGen,
        code_gen_hook: CodeGenHook,
    ) -> Parser:
        binder = self._get_binder()
        ctx_namespace = BuiltinContextNamespace()
        extraction_code_builder = extraction_gen.generate_input_extraction(binder, ctx_namespace, fields_parsers)
        creation_code_builder = creation_gen.generate_input_creation(binder, ctx_namespace)

        return compile_closure_with_globals_capturing(
            compiler=self._get_compiler(),
            code_gen_hook=code_gen_hook,
            binder=binder,
            namespace=ctx_namespace.dict,
            body_builders=[
                extraction_code_builder,
                creation_code_builder,
            ],
            closure_name=self._get_closure_name(request),
            file_name=self._get_file_name(request),
        )
