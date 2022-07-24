from typing import Mapping, Protocol, Tuple

from ...code_tools import BasicClosureCompiler, BuiltinContextNamespace
from ...common import Parser
from ...provider.essential import CannotProvide, Mediator
from ...provider.model.definitions import CodeGenerator, InputFigure, InputFigureRequest, VarBinder
from ...provider.model.input_extraction_gen import BuiltinInputExtractionGen
from ...provider.provider_template import ParserProvider
from ...provider.request_cls import ParserFieldRequest, ParserRequest
from .basic_gen import (
    CodeGenHookRequest,
    NameSanitizer,
    compile_closure_with_globals_capturing,
    get_skipped_fields,
    strip_figure,
    stub_code_gen_hook,
)
from .crown_definitions import (
    ExtraCollect,
    InpCrown,
    InpDictCrown,
    InpFieldCrown,
    InpListCrown,
    InpNoneCrown,
    InputNameMapping,
    InputNameMappingRequest,
)
from .input_creation_gen import BuiltinInputCreationGen


class InputExtractionMaker(Protocol):
    def __call__(self, mediator: Mediator, request: ParserRequest) -> Tuple[CodeGenerator, InputFigure]:
        pass


class InputCreationMaker(Protocol):
    def __call__(self, mediator: Mediator, request: ParserRequest, figure: InputFigure) -> CodeGenerator:
        pass


class BuiltinInputExtractionMaker(InputExtractionMaker):
    def __call__(self, mediator: Mediator, request: ParserRequest) -> Tuple[CodeGenerator, InputFigure]:
        figure: InputFigure = mediator.provide(
            InputFigureRequest(type=request.type)
        )

        name_mapping = mediator.provide(
            InputNameMappingRequest(
                type=request.type,
                figure=figure,
            )
        )

        processed_figure = self._process_figure(figure, name_mapping)

        if processed_figure.extra is None and self._has_collect_policy(name_mapping.crown):
            raise CannotProvide(
                "Cannot create parser that collect extra data"
                " if InputFigure does not take extra data",
                is_important=True,
            )

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
                    param_name=field.param_name,
                )
            )
            for field in processed_figure.fields
        }

        extraction_gen = self._create_extraction_gen(request, figure, name_mapping, field_parsers)

        return extraction_gen, figure

    def _process_figure(self, figure: InputFigure, name_mapping: InputNameMapping) -> InputFigure:
        skipped_fields = get_skipped_fields(figure, name_mapping)

        skipped_required_fields = [
            field.name
            for field in figure.fields
            if field.is_required and field.name in skipped_fields
        ]

        if skipped_required_fields:
            raise ValueError(
                f"Required fields {skipped_required_fields} are skipped"
            )

        return strip_figure(figure, skipped_fields)

    def _create_extraction_gen(
        self,
        request: ParserRequest,
        figure: InputFigure,
        name_mapping: InputNameMapping,
        field_parsers: Mapping[str, Parser],
    ) -> CodeGenerator:
        return BuiltinInputExtractionGen(
            figure=figure,
            crown=name_mapping.crown,
            debug_path=request.debug_path,
            field_parsers=field_parsers,
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


def make_input_creation(mediator: Mediator, request: ParserRequest, figure: InputFigure) -> CodeGenerator:
    return BuiltinInputCreationGen(figure=figure)


class ModelParserProvider(ParserProvider):
    def __init__(
        self,
        name_sanitizer: NameSanitizer,
        extraction_maker: InputExtractionMaker,
        creation_maker: InputCreationMaker,
    ):
        self._name_sanitizer = name_sanitizer
        self._extraction_maker = extraction_maker
        self._creation_maker = creation_maker

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        extraction_gen, figure = self._extraction_maker(mediator, request)
        creation_gen = self._creation_maker(mediator, request, figure)

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
