from typing import Dict, Protocol, Tuple

from ...code_tools import BasicClosureCompiler, BuiltinContextNamespace
from ...common import Serializer
from ...model_tools import OutputField
from ...provider.essential import CannotProvide, Mediator
from ...provider.model.definitions import CodeGenerator, OutputFigure, OutputFigureRequest, VarBinder
from ...provider.provider_template import SerializerProvider
from ...provider.request_cls import SerializerFieldRequest, SerializerRequest
from .basic_gen import (
    CodeGenHookRequest,
    NameSanitizer,
    compile_closure_with_globals_capturing,
    get_skipped_fields,
    strip_figure,
    stub_code_gen_hook,
)
from .crown_definitions import (
    OutCrown,
    OutDictCrown,
    OutFieldCrown,
    OutListCrown,
    OutNoneCrown,
    OutputNameMapping,
    OutputNameMappingRequest,
)
from .output_creation_gen import BuiltinOutputCreationGen
from .output_extraction_gen import BuiltinOutputExtractionGen


class OutputExtractionMaker(Protocol):
    def __call__(self, mediator: Mediator, request: SerializerRequest, figure: OutputFigure) -> CodeGenerator:
        pass


class OutputCreationMaker(Protocol):
    def __call__(self, mediator: Mediator, request: SerializerRequest) -> Tuple[CodeGenerator, OutputFigure]:
        pass


def make_output_extraction(mediator: Mediator, request: SerializerRequest, figure: OutputFigure) -> CodeGenerator:
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
        for field in figure.fields
    }

    return BuiltinOutputExtractionGen(
        figure=figure,
        debug_path=request.debug_path,
        field_serializers=field_serializers,
    )


class BuiltinOutputCreationMaker(OutputCreationMaker):
    def __call__(self, mediator: Mediator, request: SerializerRequest) -> Tuple[CodeGenerator, OutputFigure]:
        figure: OutputFigure = mediator.provide(
            OutputFigureRequest(type=request.type)
        )

        name_mapping = mediator.provide(
            OutputNameMappingRequest(
                type=request.type,
                figure=figure,
            )
        )

        processed_figure = self._process_figure(figure, name_mapping)
        creation_gen = self._create_creation_gen(request, processed_figure, name_mapping)
        return creation_gen, processed_figure

    def _process_figure(self, figure: OutputFigure, name_mapping: OutputNameMapping) -> OutputFigure:
        fields_dict = {field.name: field for field in figure.fields}
        self._check_optional_field_at_list_crown(fields_dict, name_mapping.crown)
        return strip_figure(figure, get_skipped_fields(figure, name_mapping))

    def _create_creation_gen(
        self,
        request: SerializerRequest,
        figure: OutputFigure,
        name_mapping: OutputNameMapping,
    ) -> CodeGenerator:
        return BuiltinOutputCreationGen(
            figure=figure,
            crown=name_mapping.crown,
            debug_path=request.debug_path,
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
                self._check_optional_field_at_list_crown(fields_dict, crown)
        elif not isinstance(crown, (OutFieldCrown, OutNoneCrown)):
            raise TypeError


class ModelSerializerProvider(SerializerProvider):
    def __init__(
        self,
        name_sanitizer: NameSanitizer,
        extraction_maker: OutputExtractionMaker,
        creation_maker: OutputCreationMaker,
    ):
        self._name_sanitizer = name_sanitizer
        self._extraction_maker = extraction_maker
        self._creation_maker = creation_maker

    def _provide_serializer(self, mediator: Mediator, request: SerializerRequest) -> Serializer:
        creation_gen, figure = self._creation_maker(mediator, request)
        extraction_gen = self._extraction_maker(mediator, request, figure)

        try:
            code_gen_hook = mediator.provide(CodeGenHookRequest())
        except CannotProvide:
            code_gen_hook = stub_code_gen_hook

        binder = self._get_binder()
        ctx_namespace = BuiltinContextNamespace()

        extraction_code_builder = extraction_gen(binder, ctx_namespace)
        creation_code_builder = creation_gen(binder, ctx_namespace)

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
