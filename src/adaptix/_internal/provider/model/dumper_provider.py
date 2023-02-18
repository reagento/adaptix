from typing import Protocol, Tuple

from ...code_tools import BasicClosureCompiler, BuiltinContextNamespace
from ...common import Dumper
from ..essential import CannotProvide, Mediator
from ..provider_template import DumperProvider
from ..request_cls import DumperRequest, OutputFieldLocation, TypeHintLocation
from .basic_gen import (
    CodeGenHookRequest,
    NameSanitizer,
    compile_closure_with_globals_capturing,
    get_extra_targets_at_crown,
    get_optional_fields_at_list_crown,
    get_skipped_fields,
    get_wild_extra_targets,
    strip_figure_fields,
    stub_code_gen_hook,
)
from .crown_definitions import OutExtraMove, OutputNameLayout, OutputNameLayoutRequest
from .definitions import CodeGenerator, OutputFigure, OutputFigureRequest, VarBinder
from .output_creation_gen import BuiltinOutputCreationGen
from .output_extraction_gen import BuiltinOutputExtractionGen


class OutputExtractionMaker(Protocol):
    def __call__(
        self,
        mediator: Mediator,
        request: DumperRequest,
        figure: OutputFigure,
        extra_move: OutExtraMove,
    ) -> CodeGenerator:
        ...


class OutputCreationMaker(Protocol):
    def __call__(
        self,
        mediator: Mediator,
        request: DumperRequest,
    ) -> Tuple[CodeGenerator, OutputFigure, OutExtraMove]:
        ...


def make_output_extraction(
    mediator: Mediator,
    request: DumperRequest,
    figure: OutputFigure,
    extra_move: OutExtraMove,
) -> CodeGenerator:
    field_dumpers = {
        field.name: mediator.provide(
            DumperRequest(
                loc=OutputFieldLocation(**vars(field)),
                debug_path=request.debug_path,
            )
        )
        for field in figure.fields
    }

    return BuiltinOutputExtractionGen(
        figure=figure,
        extra_move=extra_move,
        debug_path=request.debug_path,
        fields_dumpers=field_dumpers,
    )


class BuiltinOutputCreationMaker(OutputCreationMaker):
    def __call__(self, mediator: Mediator, request: DumperRequest) -> Tuple[CodeGenerator, OutputFigure, OutExtraMove]:
        figure: OutputFigure = mediator.provide(
            OutputFigureRequest(loc=request.loc)
        )

        name_layout = mediator.provide(
            OutputNameLayoutRequest(
                loc=request.loc,
                figure=figure,
            )
        )

        processed_figure = self._process_figure(figure, name_layout)
        creation_gen = self._create_creation_gen(request, processed_figure, name_layout)
        return creation_gen, processed_figure, name_layout.extra_move

    def _process_figure(self, figure: OutputFigure, name_layout: OutputNameLayout) -> OutputFigure:
        optional_fields_at_list_crown = get_optional_fields_at_list_crown(
            {field.name: field for field in figure.fields},
            name_layout.crown,
        )
        if optional_fields_at_list_crown:
            raise ValueError(
                f"Optional fields {optional_fields_at_list_crown} are found at list crown"
            )

        wild_extra_targets = get_wild_extra_targets(figure, name_layout.extra_move)
        if wild_extra_targets:
            raise ValueError(
                f"ExtraTargets {wild_extra_targets} are attached to non-existing fields"
            )

        extra_targets_at_crown = get_extra_targets_at_crown(name_layout)
        if extra_targets_at_crown:
            raise ValueError(
                f"Extra targets {extra_targets_at_crown} are found at crown"
            )

        return strip_figure_fields(figure, get_skipped_fields(figure, name_layout))

    def _create_creation_gen(
        self,
        request: DumperRequest,
        figure: OutputFigure,
        name_layout: OutputNameLayout,
    ) -> CodeGenerator:
        return BuiltinOutputCreationGen(
            figure=figure,
            name_layout=name_layout,
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
        creation_gen, figure, extra_move = self._creation_maker(mediator, request)
        extraction_gen = self._extraction_maker(mediator, request, figure, extra_move)

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
        if isinstance(request.loc, TypeHintLocation):
            tp = request.loc.type
            if isinstance(tp, type):
                name = tp.__name__
            else:
                name = str(tp)
        else:
            name = ''

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
