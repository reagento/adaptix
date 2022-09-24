from typing import Protocol, Tuple

from ...code_tools import BasicClosureCompiler, BuiltinContextNamespace
from ...common import Dumper
from ...provider.essential import CannotProvide, Mediator
from ...provider.model.definitions import CodeGenerator, OutputFigure, OutputFigureRequest, VarBinder
from ...provider.provider_template import DumperProvider
from ...provider.request_cls import DumperFieldRequest, DumperRequest
from .basic_gen import (
    CodeGenHookRequest,
    NameSanitizer,
    compile_closure_with_globals_capturing,
    get_extra_targets_at_crown,
    get_optional_fields_at_list_crown,
    get_skipped_fields,
    strip_figure,
    stub_code_gen_hook,
)
from .crown_definitions import OutputNameMapping, OutputNameMappingRequest
from .output_creation_gen import BuiltinOutputCreationGen
from .output_extraction_gen import BuiltinOutputExtractionGen


class OutputExtractionMaker(Protocol):
    def __call__(self, mediator: Mediator, request: DumperRequest, figure: OutputFigure) -> CodeGenerator:
        ...


class OutputCreationMaker(Protocol):
    def __call__(self, mediator: Mediator, request: DumperRequest) -> Tuple[CodeGenerator, OutputFigure]:
        ...


def make_output_extraction(mediator: Mediator, request: DumperRequest, figure: OutputFigure) -> CodeGenerator:
    field_dumpers = {
        field.name: mediator.provide(
            DumperFieldRequest(
                debug_path=request.debug_path,
                field=field,
                type=field.type,
            )
        )
        for field in figure.fields
    }

    return BuiltinOutputExtractionGen(
        figure=figure,
        debug_path=request.debug_path,
        field_dumpers=field_dumpers,
    )


class BuiltinOutputCreationMaker(OutputCreationMaker):
    def __call__(self, mediator: Mediator, request: DumperRequest) -> Tuple[CodeGenerator, OutputFigure]:
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
        optional_fields_at_list_crown = get_optional_fields_at_list_crown(
            {field.name: field for field in figure.fields},
            name_mapping.crown,
        )
        if optional_fields_at_list_crown:
            raise ValueError(
                f"Optional fields {optional_fields_at_list_crown} are found at list crown"
            )

        extra_targets_at_crown = get_extra_targets_at_crown(figure, name_mapping)
        if extra_targets_at_crown:
            raise ValueError(
                f"Extra targets {extra_targets_at_crown} are found at crown"
            )

        return strip_figure(figure, get_skipped_fields(figure, name_mapping))

    def _create_creation_gen(
        self,
        request: DumperRequest,
        figure: OutputFigure,
        name_mapping: OutputNameMapping,
    ) -> CodeGenerator:
        return BuiltinOutputCreationGen(
            figure=figure,
            crown=name_mapping.crown,
            debug_path=request.debug_path,
        )


class ModelDumperProvider(DumperProvider):
    def __init__(
        self,
        name_sanitizer: NameSanitizer,
        extraction_maker: OutputExtractionMaker,
        creation_maker: OutputCreationMaker,
    ):
        self._name_sanitizer = name_sanitizer
        self._extraction_maker = extraction_maker
        self._creation_maker = creation_maker

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
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

    def _get_closure_name(self, request: DumperRequest) -> str:
        tp = request.type
        if isinstance(tp, type):
            name = tp.__name__
        else:
            name = str(tp)

        s_name = self._name_sanitizer.sanitize(name)
        if s_name != "":
            s_name = "_" + s_name
        return "model_dumper" + s_name

    def _get_file_name(self, request: DumperRequest) -> str:
        return self._get_closure_name(request)

    def _get_compiler(self):
        return BasicClosureCompiler()

    def _get_binder(self):
        return VarBinder()
