from typing import Dict

from .basic_gen import (
    CodeGenHookRequest, stub_code_gen_hook,
    CodeGenHook, DirectFieldsCollectorMixin, strip_figure, NameSanitizer,
    compile_closure_with_globals_capturing
)
from .crown_definitions import (
    OutputNameMappingRequest, OutputNameMapping, OutCrown, OutDictCrown,
    OutListCrown, OutFieldCrown, OutNoneCrown
)
from .output_creation_gen import BuiltinOutputCreationGen
from .output_extraction_gen import BuiltinOutputExtractionGen
from ...code_tools import BasicClosureCompiler, BuiltinContextNamespace
from ...common import Serializer
from ...model_tools import OutputField
from ...provider.essential import Mediator, CannotProvide
from ...provider.model.definitions import (
    OutputFigureRequest, VarBinder, OutputExtractionImageRequest,
    OutputExtractionImage, OutputExtractionGen, OutputCreationImageRequest, OutputCreationImage, OutputCreationGen,
    OutputFigure,
)
from ...provider.provider_template import SerializerProvider
from ...provider.request_cls import SerializerRequest, SerializerFieldRequest
from ...provider.static_provider import StaticProvider, static_provision_action


class BuiltinOutputExtractionImageProvider(StaticProvider, DirectFieldsCollectorMixin):
    @static_provision_action
    def _provide_extraction_image(
        self, mediator: Mediator, request: OutputExtractionImageRequest,
    ) -> OutputExtractionImage:
        return OutputExtractionImage(
            extraction_gen=BuiltinOutputExtractionGen(
                figure=request.figure,
                debug_path=request.initial_request.debug_path,
            ),
        )


class BuiltinOutputCreationImageProvider(StaticProvider, DirectFieldsCollectorMixin):
    @static_provision_action
    def _provide_extraction_image(self, mediator: Mediator, request: OutputCreationImageRequest) -> OutputCreationImage:
        name_mapping = mediator.provide(
            OutputNameMappingRequest(
                type=request.initial_request.type,
                figure=request.figure,
            )
        )

        fields_dict = {field.name: field for field in request.figure.fields}
        self._check_optional_field_at_list_crown(fields_dict, name_mapping.crown)

        used_direct_fields = self._collect_used_direct_fields(name_mapping.crown)
        skipped_direct_fields = [
            field.name for field in request.figure.fields
            if field.name not in used_direct_fields
        ]

        return OutputCreationImage(
            creation_gen=self._create_creation_gen(request, name_mapping),
            skipped_fields=skipped_direct_fields + list(name_mapping.skipped_extra_targets),
        )

    def _create_creation_gen(
        self,
        request: OutputCreationImageRequest,
        name_mapping: OutputNameMapping,
    ) -> OutputCreationGen:
        return BuiltinOutputCreationGen(
            figure=request.figure,
            crown=name_mapping.crown,
            debug_path=request.initial_request.debug_path,
        )

    def _check_optional_field_at_list_crown(self, fields_dict: Dict[str, OutputField], crown: OutCrown):
        if isinstance(crown, OutDictCrown):
            for sub_crown in crown.map.values():
                self._check_optional_field_at_list_crown(fields_dict, sub_crown)
        elif isinstance(crown, OutListCrown):
            for sub_crown in crown.map:
                if isinstance(sub_crown, OutFieldCrown) and fields_dict[sub_crown.name].is_optional:
                    raise CannotProvide(
                        "OutListCrown cannot contain OutFieldCrown of optional field",
                        is_important=True,
                    )
                else:
                    self._check_optional_field_at_list_crown(fields_dict, crown)
        elif not isinstance(crown, (OutFieldCrown, OutNoneCrown)):
            raise TypeError


class FieldsSerializerProvider(SerializerProvider):
    def __init__(self, name_sanitizer: NameSanitizer):
        self._name_sanitizer = name_sanitizer

    def _process_figure(self, figure: OutputFigure, creation_image: OutputCreationImage) -> OutputFigure:
        return strip_figure(figure, creation_image)

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        figure: OutputFigure = mediator.provide(
            OutputFigureRequest(type=request.type)
        )

        creation_image = mediator.provide(
            OutputCreationImageRequest(
                figure=figure,
                initial_request=request,
            )
        )

        processed_figure = self._process_figure(figure, creation_image)

        extraction_image = mediator.provide(
            OutputExtractionImageRequest(
                figure=processed_figure,
                initial_request=request,
            )
        )

        try:
            code_gen_hook = mediator.provide(CodeGenHookRequest(initial_request=request))
        except CannotProvide:
            code_gen_hook = stub_code_gen_hook

        field_serializers = {
            field.name: mediator.provide(
                SerializerFieldRequest(
                    type=field.type,
                    debug_path=request.debug_path,
                    default=field.default,
                    accessor=field.accessor,
                    metadata=field.metadata,
                    name=field.name,
                )
            )
            for field in processed_figure.fields
        }

        return self._make_serializer(
            request=request,
            creation_gen=creation_image.creation_gen,
            extraction_gen=extraction_image.extraction_gen,
            fields_serializers=field_serializers,
            code_gen_hook=code_gen_hook,
        )

    def _get_closure_name(self, request: SerializerRequest) -> str:
        tp = request.type
        if isinstance(tp, type):
            name = tp.__name__
        else:
            name = str(tp)

        s_name = self._name_sanitizer.sanitize(name)
        if s_name != "":
            s_name = "_" + s_name
        return "model_serializer" + s_name

    def _get_file_name(self, request: SerializerRequest) -> str:
        return self._get_closure_name(request)

    def _get_compiler(self):
        return BasicClosureCompiler()

    def _get_binder(self):
        return VarBinder()

    def _make_serializer(
        self,
        request: SerializerRequest,
        fields_serializers: Dict[str, Serializer],
        creation_gen: OutputCreationGen,
        extraction_gen: OutputExtractionGen,
        code_gen_hook: CodeGenHook,
    ) -> Serializer:
        binder = self._get_binder()
        ctx_namespace = BuiltinContextNamespace()
        extraction_code_builder = extraction_gen.generate_output_extraction(binder, ctx_namespace, fields_serializers)
        creation_code_builder = creation_gen.generate_output_creation(binder, ctx_namespace)

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
