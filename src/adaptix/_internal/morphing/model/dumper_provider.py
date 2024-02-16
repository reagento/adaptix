from typing import Mapping

from adaptix._internal.provider.fields import output_field_to_loc_map

from ...code_tools.compiler import BasicClosureCompiler, ClosureCompiler
from ...common import Dumper
from ...definitions import DebugTrail
from ...model_tools.definitions import OutputShape
from ...provider.essential import Mediator
from ...provider.request_cls import DebugTrailRequest, TypeHintLoc
from ...provider.shape_provider import OutputShapeRequest, provide_generic_resolved_shape
from ..provider_template import DumperProvider
from ..request_cls import DumperRequest
from .basic_gen import (
    ModelDumperGen,
    NameSanitizer,
    compile_closure_with_globals_capturing,
    fetch_code_gen_hook,
    get_extra_targets_at_crown,
    get_optional_fields_at_list_crown,
    get_wild_extra_targets,
)
from .crown_definitions import OutputNameLayout, OutputNameLayoutRequest
from .dumper_gen import BuiltinModelDumperGen


class ModelDumperProvider(DumperProvider):
    def __init__(self, *, name_sanitizer: NameSanitizer = NameSanitizer()):
        self._name_sanitizer = name_sanitizer

    def _provide_dumper(self, mediator: Mediator, request: DumperRequest) -> Dumper:
        dumper_gen = self._fetch_model_dumper_gen(mediator, request)
        closure_name = self._get_closure_name(request)
        dumper_code, dumper_namespace = dumper_gen.produce_code(closure_name=closure_name)
        return compile_closure_with_globals_capturing(
            compiler=self._get_compiler(),
            code_gen_hook=fetch_code_gen_hook(mediator, request.loc_stack),
            namespace=dumper_namespace,
            closure_code=dumper_code,
            closure_name=closure_name,
            file_name=self._get_file_name(request),
        )

    def _fetch_model_dumper_gen(self, mediator: Mediator, request: DumperRequest) -> ModelDumperGen:
        shape = self._fetch_shape(mediator, request)
        name_layout = self._fetch_name_layout(mediator, request, shape)
        self._validate_params(shape, name_layout)

        fields_dumpers = self._fetch_field_dumpers(mediator, request, shape)
        debug_trail = mediator.mandatory_provide(DebugTrailRequest(loc_stack=request.loc_stack))
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
            repr(request.last_map[TypeHintLoc].type)
            if request.last_map.has(TypeHintLoc) else
            '<unknown model>'
        )

    def _create_model_dumper_gen(
        self,
        debug_trail: DebugTrail,
        shape: OutputShape,
        name_layout: OutputNameLayout,
        fields_dumpers: Mapping[str, Dumper],
        model_identity: str,
    ) -> ModelDumperGen:
        return BuiltinModelDumperGen(
            shape=shape,
            name_layout=name_layout,
            debug_trail=debug_trail,
            fields_dumpers=fields_dumpers,
            model_identity=model_identity,
        )

    def _request_to_view_string(self, request: DumperRequest) -> str:
        if request.last_map.has(TypeHintLoc):
            tp = request.last_map[TypeHintLoc].type
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

    def _get_compiler(self) -> ClosureCompiler:
        return BasicClosureCompiler()

    def _fetch_shape(self, mediator: Mediator, request: DumperRequest) -> OutputShape:
        return provide_generic_resolved_shape(mediator, OutputShapeRequest(loc_stack=request.loc_stack))

    def _fetch_name_layout(self, mediator: Mediator, request: DumperRequest, shape: OutputShape) -> OutputNameLayout:
        return mediator.delegating_provide(
            OutputNameLayoutRequest(
                loc_stack=request.loc_stack,
                shape=shape,
            )
        )

    def _fetch_field_dumpers(
        self,
        mediator: Mediator,
        request: DumperRequest,
        shape: OutputShape,
    ) -> Mapping[str, Dumper]:
        dumpers = mediator.mandatory_provide_by_iterable(
            [
                DumperRequest(loc_stack=request.loc_stack.append_with(output_field_to_loc_map(field)))
                for field in shape.fields
            ],
            lambda: "Cannot create dumper for model. Dumpers for some fields cannot be created",
        )
        return {field.id: dumper for field, dumper in zip(shape.fields, dumpers)}

    def _validate_params(self, shape: OutputShape, name_layout: OutputNameLayout) -> None:
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
