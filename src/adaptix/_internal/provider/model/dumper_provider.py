from typing import Protocol, Tuple

from ...code_tools.compiler import BasicClosureCompiler
from ...code_tools.context_namespace import BuiltinContextNamespace
from ...common import Dumper
from ...essential import CannotProvide, Mediator
from ..definitions import DebugTrail
from ..provider_template import DumperProvider
from ..request_cls import DebugTrailRequest, DumperRequest, TypeHintLoc
from .basic_gen import (
    CodeGenHookRequest,
    NameSanitizer,
    compile_closure_with_globals_capturing,
    get_extra_targets_at_crown,
    get_optional_fields_at_list_crown,
    get_skipped_fields,
    get_wild_extra_targets,
    strip_output_shape_fields,
    stub_code_gen_hook,
)
from .crown_definitions import OutExtraMove, OutputNameLayout, OutputNameLayoutRequest
from .definitions import CodeGenerator, OutputShape, OutputShapeRequest, VarBinder
from .fields import output_field_to_loc_map
from .output_creation_gen import BuiltinOutputCreationGen
from .output_extraction_gen import BuiltinOutputExtractionGen
from .shape_provider import provide_generic_resolved_shape


class OutputExtractionMaker(Protocol):
    def __call__(
        self,
        mediator: Mediator,
        request: DumperRequest,
        shape: OutputShape,
        extra_move: OutExtraMove,
    ) -> CodeGenerator:
        ...


class OutputCreationMaker(Protocol):
    def __call__(
        self,
        mediator: Mediator,
        request: DumperRequest,
    ) -> Tuple[CodeGenerator, OutputShape, OutExtraMove]:
        ...


def make_output_extraction(
    mediator: Mediator,
    request: DumperRequest,
    shape: OutputShape,
    extra_move: OutExtraMove,
) -> CodeGenerator:
    field_dumpers = {
        field.id: mediator.provide(
            DumperRequest(
                loc_map=output_field_to_loc_map(field),
            )
        )
        for field in shape.fields
    }
    debug_trail = mediator.provide(DebugTrailRequest(loc_map=request.loc_map))
    return BuiltinOutputExtractionGen(
        shape=shape,
        extra_move=extra_move,
        debug_trail=debug_trail,
        fields_dumpers=field_dumpers,
    )


class BuiltinOutputCreationMaker(OutputCreationMaker):
    def __call__(self, mediator: Mediator, request: DumperRequest) -> Tuple[CodeGenerator, OutputShape, OutExtraMove]:
        shape = provide_generic_resolved_shape(mediator, OutputShapeRequest(loc_map=request.loc_map))

        name_layout = mediator.provide(
            OutputNameLayoutRequest(
                loc_map=request.loc_map,
                shape=shape,
            )
        )

        processed_shape = self._process_shape(shape, name_layout)
        debug_trail = mediator.provide(DebugTrailRequest(loc_map=request.loc_map))
        creation_gen = self._create_creation_gen(debug_trail, processed_shape, name_layout)
        return creation_gen, processed_shape, name_layout.extra_move

    def _process_shape(self, shape: OutputShape, name_layout: OutputNameLayout) -> OutputShape:
        optional_fields_at_list_crown = get_optional_fields_at_list_crown(
            {field.id: field for field in shape.fields},
            name_layout.crown,
        )
        if optional_fields_at_list_crown:
            raise ValueError(
                f"Optional fields {optional_fields_at_list_crown} are found at list crown"
            )

        wild_extra_targets = get_wild_extra_targets(shape, name_layout.extra_move)
        if wild_extra_targets:
            raise ValueError(
                f"ExtraTargets {wild_extra_targets} are attached to non-existing fields"
            )

        extra_targets_at_crown = get_extra_targets_at_crown(name_layout)
        if extra_targets_at_crown:
            raise ValueError(
                f"Extra targets {extra_targets_at_crown} are found at crown"
            )

        return strip_output_shape_fields(shape, get_skipped_fields(shape, name_layout))

    def _create_creation_gen(
        self,
        debug_trail: DebugTrail,
        shape: OutputShape,
        name_layout: OutputNameLayout,
    ) -> CodeGenerator:
        return BuiltinOutputCreationGen(
            shape=shape,
            name_layout=name_layout,
            debug_trail=debug_trail,
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
        creation_gen, shape, extra_move = self._creation_maker(mediator, request)
        extraction_gen = self._extraction_maker(mediator, request, shape, extra_move)

        try:
            code_gen_hook = mediator.provide(CodeGenHookRequest())
        except CannotProvide:
            code_gen_hook = stub_code_gen_hook

        binder = self._get_binder()
        ctx_namespace = BuiltinContextNamespace()

        extraction_code_builder = extraction_gen.produce_code(binder, ctx_namespace)
        creation_code_builder = creation_gen.produce_code(binder, ctx_namespace)

        return compile_closure_with_globals_capturing(
            compiler=self._get_compiler(),
            code_gen_hook=code_gen_hook,
            namespace=ctx_namespace.dict,
            body_builders=[
                extraction_code_builder,
                creation_code_builder,
            ],
            closure_name=self._get_closure_name(request),
            closure_params=binder.data,
            file_name=self._get_file_name(request),
        )

    def _get_closure_name(self, request: DumperRequest) -> str:
        if request.loc_map.has(TypeHintLoc):
            tp = request.loc_map[TypeHintLoc].type
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
