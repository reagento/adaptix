from typing import Mapping

from ...code_tools.compiler import BasicClosureCompiler
from ...code_tools.context_namespace import BuiltinContextNamespace
from ...common import Dumper
from ...definitions import DebugTrail
from ...provider.essential import CannotProvide, Mediator
from ...provider.request_cls import DebugTrailRequest, TypeHintLoc
from ..provider_template import DumperProvider
from ..request_cls import DumperRequest
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
from .crown_definitions import OutputNameLayout, OutputNameLayoutRequest
from .definitions import CodeGenerator, OutputShape, OutputShapeRequest
from .dumper_gen import ModelDumperGen
from .fields import output_field_to_loc_map
from .shape_provider import provide_generic_resolved_shape


class ModelDumperProvider(DumperProvider):
    def __init__(self, *, name_sanitizer: NameSanitizer = NameSanitizer()):
        self._name_sanitizer = name_sanitizer

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        dumper_gen = self._fetch_model_dumper_gen(mediator, request)
        ctx_namespace = BuiltinContextNamespace()
        dumper_code_builder = dumper_gen.produce_code(ctx_namespace)

        try:
            code_gen_hook = mediator.delegating_provide(CodeGenHookRequest())
        except CannotProvide:
            code_gen_hook = stub_code_gen_hook

        return compile_closure_with_globals_capturing(
            compiler=self._get_compiler(),
            code_gen_hook=code_gen_hook,
            namespace=ctx_namespace.dict,
            body_builders=[dumper_code_builder],
            closure_name=self._get_closure_name(request),
            closure_params='data',
            file_name=self._get_file_name(request),
        )

    def _fetch_model_dumper_gen(self, mediator: Mediator, request: DumperRequest) -> CodeGenerator:
        shape = self._fetch_shape(mediator, request)
        name_layout = self._fetch_name_layout(mediator, request, shape)
        shape = self._process_shape(shape, name_layout)

        fields_dumpers = self._fetch_field_dumpers(mediator, request, shape)
        debug_trail = mediator.mandatory_provide(DebugTrailRequest(loc_map=request.loc_map))
        return self._create_model_dumper_gen(
            debug_trail=debug_trail,
            shape=shape,
            name_layout=name_layout,
            fields_dumpers=fields_dumpers,
            model_identity=self._fetch_model_identity(mediator, request, shape, name_layout),
        )

    def _fetch_model_identity(
        self,
        mediator: Mediator,
        request: DumperRequest,
        shape: OutputShape,
        name_layout: OutputNameLayout,
    ) -> str:
        return (
            repr(request.loc_map[TypeHintLoc].type)
            if request.loc_map.has(TypeHintLoc) else
            '<unknown model>'
        )

    def _create_model_dumper_gen(
        self,
        debug_trail: DebugTrail,
        shape: OutputShape,
        name_layout: OutputNameLayout,
        fields_dumpers: Mapping[str, Dumper],
        model_identity: str,
    ) -> CodeGenerator:
        return ModelDumperGen(
            shape=shape,
            name_layout=name_layout,
            debug_trail=debug_trail,
            fields_dumpers=fields_dumpers,
            model_identity=model_identity,
        )

    def _request_to_view_string(self, request: DumperRequest) -> str:
        if request.loc_map.has(TypeHintLoc):
            tp = request.loc_map[TypeHintLoc].type
            if isinstance(tp, type):
                return tp.__name__
            return str(tp)
        return ''

    def _merge_view_string(self, *fragments: str) -> str:
        return '_'.join(filter(None, fragments))

    def _get_file_name(self, request: DumperRequest) -> str:
        return self._merge_view_string(
            'model_dumper', self._request_to_view_string(request),
        )

    def _get_closure_name(self, request: DumperRequest) -> str:
        return self._merge_view_string(
            'model_dumper', self._name_sanitizer.sanitize(self._request_to_view_string(request)),
        )

    def _get_compiler(self):
        return BasicClosureCompiler()

    def _fetch_shape(self, mediator: Mediator, request: DumperRequest) -> OutputShape:
        return provide_generic_resolved_shape(mediator, OutputShapeRequest(loc_map=request.loc_map))

    def _fetch_name_layout(self, mediator: Mediator, request: DumperRequest, shape: OutputShape) -> OutputNameLayout:
        return mediator.delegating_provide(
            OutputNameLayoutRequest(
                loc_map=request.loc_map,
                shape=shape,
            )
        )

    def _fetch_field_dumpers(
        self,
        mediator: Mediator,
        request: DumperRequest,
        shape: OutputShape,
    ) -> Mapping[str, Dumper]:
        owner_type = request.loc_map[TypeHintLoc].type
        dumpers = mediator.mandatory_provide_by_iterable(
            [
                DumperRequest(loc_map=output_field_to_loc_map(owner_type, field))
                for field in shape.fields
            ],
            lambda: "Cannot create dumper for model. Dumpers for some fields cannot be created",
        )
        return {field.id: dumper for field, dumper in zip(shape.fields, dumpers)}

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
