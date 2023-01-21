from typing import Mapping, Protocol, Tuple

from ...code_tools import BasicClosureCompiler, BuiltinContextNamespace
from ...common import Loader
from ..essential import CannotProvide, Mediator
from ..model.definitions import CodeGenerator, InputFigure, InputFigureRequest, VarBinder
from ..model.input_extraction_gen import BuiltinInputExtractionGen
from ..provider_template import LoaderProvider
from ..request_cls import InputFieldLocation, LoaderRequest, TypeHintLocation
from .basic_gen import (
    CodeGenHookRequest,
    NameSanitizer,
    compile_closure_with_globals_capturing,
    get_extra_targets_at_crown,
    get_optional_fields_at_list_crown,
    get_skipped_fields,
    get_wild_extra_targets,
    has_collect_policy,
    strip_figure_fields,
    stub_code_gen_hook,
)
from .crown_definitions import InpExtraMove, InputNameLayout, InputNameLayoutRequest
from .input_creation_gen import BuiltinInputCreationGen


class InputExtractionMaker(Protocol):
    def __call__(
        self,
        mediator: Mediator,
        request: LoaderRequest,
    ) -> Tuple[CodeGenerator, InputFigure, InpExtraMove]:
        ...


class InputCreationMaker(Protocol):
    def __call__(
        self,
        mediator: Mediator,
        request: LoaderRequest,
        figure: InputFigure,
        extra_move: InpExtraMove,
    ) -> CodeGenerator:
        ...


class BuiltinInputExtractionMaker(InputExtractionMaker):
    def __call__(self, mediator: Mediator, request: LoaderRequest) -> Tuple[CodeGenerator, InputFigure, InpExtraMove]:
        figure: InputFigure = mediator.provide(
            InputFigureRequest(loc=request.loc)
        )

        name_layout: InputNameLayout = mediator.provide(
            InputNameLayoutRequest(
                loc=request.loc,
                figure=figure,
            )
        )

        processed_figure = self._process_figure(figure, name_layout)
        self._validate_params(processed_figure, name_layout)

        field_loaders = {
            field.name: mediator.provide(
                LoaderRequest(
                    strict_coercion=request.strict_coercion,
                    debug_path=request.debug_path,
                    loc=InputFieldLocation(**vars(field)),
                )
            )
            for field in processed_figure.fields
        }

        extraction_gen = self._create_extraction_gen(request, figure, name_layout, field_loaders)

        return extraction_gen, figure, name_layout.extra_move

    def _process_figure(self, figure: InputFigure, name_layout: InputNameLayout) -> InputFigure:
        wild_extra_targets = get_wild_extra_targets(figure, name_layout.extra_move)
        if wild_extra_targets:
            raise ValueError(
                f"ExtraTargets {wild_extra_targets} are attached to non-existing fields"
            )

        skipped_fields = get_skipped_fields(figure, name_layout)

        skipped_required_fields = [
            field.name
            for field in figure.fields
            if field.is_required and field.name in skipped_fields
        ]
        if skipped_required_fields:
            raise ValueError(
                f"Required fields {skipped_required_fields} are skipped"
            )

        return strip_figure_fields(figure, skipped_fields)

    def _validate_params(self, processed_figure: InputFigure, name_layout: InputNameLayout) -> None:
        if name_layout.extra_move is None and has_collect_policy(name_layout.crown):
            raise ValueError(
                "Cannot create loader that collect extra data"
                " if InputFigure does not take extra data",
            )

        extra_targets_at_crown = get_extra_targets_at_crown(name_layout)
        if extra_targets_at_crown:
            raise ValueError(
                f"Extra targets {extra_targets_at_crown} are found at crown"
            )

        optional_fields_at_list_crown = get_optional_fields_at_list_crown(
            {field.name: field for field in processed_figure.fields},
            name_layout.crown,
        )
        if optional_fields_at_list_crown:
            raise ValueError(
                f"Optional fields {optional_fields_at_list_crown} are found at list crown"
            )

    def _create_extraction_gen(
        self,
        request: LoaderRequest,
        figure: InputFigure,
        name_layout: InputNameLayout,
        field_loaders: Mapping[str, Loader],
    ) -> CodeGenerator:
        return BuiltinInputExtractionGen(
            figure=figure,
            name_layout=name_layout,
            debug_path=request.debug_path,
            field_loaders=field_loaders,
        )


def make_input_creation(
    mediator: Mediator,
    request: LoaderRequest,
    figure: InputFigure,
    extra_move: InpExtraMove,
) -> CodeGenerator:
    return BuiltinInputCreationGen(figure=figure, extra_move=extra_move)


class ModelLoaderProvider(LoaderProvider):
    def __init__(
        self,
        name_sanitizer: NameSanitizer,
        extraction_maker: InputExtractionMaker,
        creation_maker: InputCreationMaker,
    ):
        self._name_sanitizer = name_sanitizer
        self._extraction_maker = extraction_maker
        self._creation_maker = creation_maker

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        extraction_gen, figure, extra_move = self._extraction_maker(mediator, request)
        creation_gen = self._creation_maker(mediator, request, figure, extra_move)

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

    def _get_closure_name(self, request: LoaderRequest) -> str:
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
        return "model_loader" + s_name

    def _get_file_name(self, request: LoaderRequest) -> str:
        return self._get_closure_name(request)

    def _get_compiler(self):
        return BasicClosureCompiler()

    def _get_binder(self):
        return VarBinder()
