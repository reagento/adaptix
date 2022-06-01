import string
from dataclasses import replace
from typing import Dict, Any

from dataclass_factory_30.code_tools import BasicClosureCompiler, CodeBuilder
from dataclass_factory_30.code_tools.context_namespace import ContextNamespace
from dataclass_factory_30.common import Parser
from dataclass_factory_30.provider import ParserProvider, ParserRequest, Mediator, ParserFieldRequest, CannotProvide
from dataclass_factory_30.provider.fields.basic_gen import (
    CodeGenHookRequest, stub_code_gen_hook,
    CodeGenHook, CodeGenHookData
)
from dataclass_factory_30.provider.fields.definitions import (
    InputFigureRequest, ExtractionImageRequest, ExtraTargets,
    InputFigure, ExtractionImage, CreationImageRequest,
    CreationGen, ExtractionGen, VarBinder
)

_AVAILABLE_CHARS = set(string.ascii_letters + string.digits)


class FieldsParserProvider(ParserProvider):
    def _process_figure(self, figure: InputFigure, extraction_image: ExtractionImage) -> InputFigure:
        skipped_required_fields = [
            field.name
            for field in figure.fields
            if field.is_required and field.name in extraction_image.skipped_fields
        ]

        if skipped_required_fields:
            raise ValueError(
                f"Required fields {skipped_required_fields} are skipped"
            )

        extra = figure.extra
        if isinstance(extra, ExtraTargets):
            extra = ExtraTargets(
                tuple(
                    field_name for field_name in extra.fields
                    if field_name not in extraction_image.skipped_fields
                )
            )

        # leave only fields that will be passed to constructor
        new_figure = replace(
            figure,
            fields=tuple(
                field for field in figure.fields
                if field.name not in extraction_image.skipped_fields
            ),
            extra=extra,
        )

        return new_figure

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        figure = mediator.provide(
            InputFigureRequest(type=request.type)
        )

        extraction_image = mediator.provide(
            ExtractionImageRequest(
                figure=figure,
                initial_request=request,
            )
        )

        processed_figure = self._process_figure(figure, extraction_image)

        creation_image = mediator.provide(
            CreationImageRequest(
                figure=processed_figure,
                initial_request=request,
            )
        )

        if name_mapping.crown.extra == ExtraCollect() and figure.extra is None:
            raise CannotProvide(
                "Cannot create parser that collect extra data"
                " if InputFigure does not take extra data"
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
            field_parsers=field_parsers,
            code_gen_hook=code_gen_hook,
        )

    def _sanitize_name(self, name: str):
        if name == "":
            return ""

        first_letter = name[0]

        if first_letter not in string.ascii_letters:
            return self._sanitize_name(name[1:])

        return first_letter + "".join(
            c for c in name[1:] if c in _AVAILABLE_CHARS
        )

    def _get_closure_name(self, request: ParserRequest) -> str:
        tp = request.type
        if isinstance(tp, type):
            name = tp.__name__
        else:
            name = str(tp)

        s_name = self._sanitize_name(name)
        if s_name != "":
            s_name = "_" + s_name
        return "fields_parser" + s_name

    def _get_file_name(self, request: ParserRequest) -> str:
        return self._get_closure_name(request)

    def _get_compiler(self):
        return BasicClosureCompiler()

    def _get_binder(self):
        return VarBinder()

    def _make_parser(
        self,
        request: ParserRequest,
        field_parsers: Dict[str, Parser],
        creation_gen: CreationGen,
        extraction_gen: ExtractionGen,
        code_gen_hook: CodeGenHook,
    ) -> Parser:
        compiler = self._get_compiler()
        binder = self._get_binder()

        namespace_dict: Dict[str, Any] = {}
        ctx_namespace = ContextNamespace(namespace_dict)

        extraction_code_builder = extraction_gen.generate_extraction(binder, ctx_namespace, field_parsers)
        creation_code_builder = creation_gen.generate_creation(binder, ctx_namespace)

        closure_name = self._get_closure_name(request)
        file_name = self._get_file_name(request)

        builder = CodeBuilder()

        global_namespace_dict = {}
        for name, value in namespace_dict.items():
            global_name = f"g_{name}"
            global_namespace_dict[global_name] = value
            builder += f"{name} = {global_name}"

        builder.empty_line()

        with builder(f"def {closure_name}({binder.data}):"):
            builder.extend(extraction_code_builder)
            builder.extend(creation_code_builder)

        builder += f"return {closure_name}"

        code_gen_hook(
            CodeGenHookData(
                namespace=global_namespace_dict,
                source=builder.string(),
            )
        )

        return compiler.compile(
            builder,
            file_name,
            global_namespace_dict,
        )
