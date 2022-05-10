import contextlib
import itertools
import string
from collections import deque
from dataclasses import replace
from random import Random
from typing import Dict, Set, Union, TypeVar, Iterable, List, Collection

from .basic_gen import (
    CodeGenHook,
    stub_code_gen_hook, CodeGenHookRequest, VarBinder, CodeGenHookData,
)
from .creation_gen import CreationGen
from .field_mapping_gen import FieldMappingGen
from .fmg_definitions import ExtraCollect, BaseCrown, BaseDictCrown, BaseFieldCrown, BaseNameMapping, BaseListCrown
from .parser_gen import RootCrown
from .. import FieldRM, ExtraTargets
from ..essential import Mediator, CannotProvide
from .definitions import (
    InputFigure, BaseFigure,

)
from ..provider_template import ParserProvider
from ..request_cls import ParserRequest, ParserFieldRequest
from ...code_tools import BasicClosureCompiler, ClosureCompiler, CodeBuilder
from ...code_tools.name_allocator import NameAllocator, Namespace, DefaultNameAllocator, PrefixSolver
from ...common import Parser

_AVAILABLE_CHARS = set(string.ascii_letters + string.digits)


class NameSanitizer:
    def sanitize(self, name: str) -> str:
        if name == "":
            return ""

        first_letter = name[0]

        if first_letter not in string.ascii_letters:
            return self.sanitize(name[1:])

        return first_letter + "".join(
            c for c in name[1:] if c in _AVAILABLE_CHARS
        )


T = TypeVar('T')


def _merge_iters(args: Iterable[Iterable[T]]) -> List[T]:
    return list(itertools.chain.from_iterable(args))


FF_TV = TypeVar("FF_TV", bound=BaseFigure)


class FigureProcessor:
    """FigureProcessor takes InputFigure and NameMapping,
    produces new InputFigure discarding unused fields
    and validates NameMapping
    """

    def _inner_collect_used_direct_fields(self, crown: BaseCrown) -> List[str]:
        if isinstance(crown, BaseDictCrown):
            return _merge_iters(
                self._inner_collect_used_direct_fields(sub_crown)
                for sub_crown in crown.map.values()
            )
        if isinstance(crown, BaseListCrown):
            return _merge_iters(
                self._inner_collect_used_direct_fields(sub_crown)
                for sub_crown in crown.map
            )
        if isinstance(crown, BaseFieldCrown):
            return [crown.name]
        if crown is None:
            return []
        raise TypeError

    def _collect_used_direct_fields(self, crown: BaseCrown) -> Set[str]:
        lst = self._inner_collect_used_direct_fields(crown)

        used_set = set()
        for f_name in lst:
            if f_name in used_set:
                raise ValueError(f"Field {f_name!r} is duplicated at crown")
            used_set.add(f_name)

        return used_set

    def _field_is_skipped(
        self,
        field: FieldRM,
        used_extra_targets: Collection[str],
        used_direct_fields: Set[str],
        extra_targets: Set[str]
    ):
        f_name = field.name
        if f_name in extra_targets:
            return f_name not in used_extra_targets
        else:
            return f_name not in used_direct_fields

    def _validate_required_fields(
        self,
        figure: BaseFigure,
        used_direct_fields: Set[str],
        extra_targets: Set[str],
        name_mapping: BaseNameMapping,
    ):
        skipped_required_fields = [
            field.name
            for field in figure.fields
            if field.is_required and self._field_is_skipped(
                field,
                used_extra_targets=name_mapping.used_extra_targets,
                used_direct_fields=used_direct_fields,
                extra_targets=extra_targets,
            )
        ]
        if skipped_required_fields:
            raise ValueError(
                f"Required fields {skipped_required_fields} not presented at not used at name_mapping"
            )

    def _get_extra_targets(self, figure: BaseFigure, used_direct_fields: Set[str]):
        if isinstance(figure.extra, ExtraTargets):
            extra_targets = set(figure.extra.fields)

            extra_targets_at_crown = used_direct_fields & extra_targets
            if extra_targets_at_crown:
                raise ValueError(
                    f"Fields {extra_targets_at_crown} can not be extra target"
                    f" and be presented at crown"
                )

            return extra_targets

        return set()

    def process_figure(self, figure: FF_TV, name_mapping: BaseNameMapping) -> FF_TV:
        # direct fields -- fields that is not an extra target
        used_direct_fields = self._collect_used_direct_fields(name_mapping.crown)
        extra_targets = self._get_extra_targets(figure, used_direct_fields)

        self._validate_required_fields(
            figure=figure,
            used_direct_fields=used_direct_fields,
            extra_targets=extra_targets,
            name_mapping=name_mapping,
        )

        extra = figure.extra

        if isinstance(extra, ExtraTargets):
            extra = ExtraTargets(tuple(extra_targets & set(name_mapping.used_extra_targets)))

        # leave only fields that will be passed to constructor
        new_figure = replace(
            figure,
            fields=tuple(
                field for field in figure.fields
                if not self._field_is_skipped(
                    field,
                    used_extra_targets=name_mapping.used_extra_targets,
                    used_direct_fields=used_direct_fields,
                    extra_targets=extra_targets,
                )
            ),
            extra=extra,
        )

        return new_figure


class FieldsParserGen:
    def __init__(self, field_mapping_gen: FieldMappingGen, creation_gen: CreationGen):
        self._field_mapping_gen = field_mapping_gen
        self._creation_gen = creation_gen

    def generate(self, closure_name: str):
        binder = VarBinder()
        creation_gen = CreationGen(figure, binder)
        field_mapping_gen = FieldMappingGen(
            figure=figure,
            binder=binder,
            crown=root_crown,
            debug_path=request.debug_path,
            strict_coercion=request.strict_coercion,
        )

        namespace = Namespace(
            predefined={closure_name},
            outer={},
            local=set(),
            prefixes=[],
            random=Random(),
        )
        namespace.add_prefix("fmg_", )

        allocator = DefaultNameAllocator(
            namespace=namespace,
            solver=PrefixSolver("fmg_")
        )

        builder = CodeBuilder()
        with builder(f"def {closure_name}({binder.data}):"):
            builder.extend(self._field_mapping_gen.generate())

            allocator.solver = PrefixSolver("cr_")
            builder.extend(self._creation_gen.generate())

        builder += f"return {closure_name}"


class FieldsParserProvider(ParserProvider):
    def _get_closure_name(self, request: ParserRequest) -> str:
        tp = request.type
        if isinstance(tp, type):
            name = tp.__name__
        else:
            name = str(tp)

        s_name = self._get_name_sanitizer().sanitize(name)
        if s_name != "":
            s_name = "_" + s_name
        return "fields_parser" + s_name

    def _get_file_name(self, request: ParserRequest) -> str:
        return self._get_closure_name(request)

    def _get_name_sanitizer(self) -> NameSanitizer:
        return NameSanitizer()

    def _get_compiler(self) -> ClosureCompiler:
        return BasicClosureCompiler()

    def _get_figure_processor(self):
        return FigureProcessor()

    def _compile(
        self,
        figure: InputFigure,
        request: ParserRequest,
        field_parsers: Dict[str, Parser],
        root_crown: RootCrown,
        code_gen_hook: CodeGenHook,
    ):

        namespace = self._create_compiler_namespace(field_parsers, state)

        code_gen_hook(CodeGenHookData(namespace=namespace, source=builder.string()))

        return compiler.compile(
            builder,
            file_name,
            namespace,
        )

    def _make_parser(
        self,
        figure: InputFigure,
        request: ParserRequest,
        field_parsers: Dict[str, Parser],
        root_crown: RootCrown,
        code_gen_hook: CodeGenHook,
    ):
        return generator.generate(
            compiler=self._get_compiler(),
            field_parsers=field_parsers,
            root_crown=root_crown,
            hook=code_gen_hook,
            closure_name=self._get_closure_name(request),
            file_name=self._get_file_name(request),
        )

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        figure: InputFigure = mediator.provide(
            InputFFRequest(type=request.type)
        )
        name_mapping: InpNameMapping = mediator.provide(
            InputNameMappingRequest(type=request.type, figure=figure)
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

        new_figure = self._get_figure_processor().process_figure(figure, name_mapping)

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
            for field in new_figure.fields
        }

        return self._make_parser(
            figure=new_figure,
            request=request,
            field_parsers=field_parsers,
            root_crown=name_mapping.crown,
            code_gen_hook=code_gen_hook,
        )
