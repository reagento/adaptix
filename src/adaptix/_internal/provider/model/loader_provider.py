from typing import Mapping

from ...code_tools.compiler import BasicClosureCompiler
from ...code_tools.context_namespace import BuiltinContextNamespace
from ...common import Loader
from ...essential import CannotProvide, Mediator
from ...model_tools.definitions import InputShape
from ..definitions import DebugTrail
from ..model.definitions import CodeGenerator, InputShapeRequest
from ..model.loader_gen import ModelLoaderGen, ModelLoaderProps
from ..provider_template import LoaderProvider
from ..request_cls import DebugTrailRequest, LoaderRequest, StrictCoercionRequest, TypeHintLoc
from .basic_gen import (
    CodeGenHookRequest,
    NameSanitizer,
    compile_closure_with_globals_capturing,
    get_extra_targets_at_crown,
    get_optional_fields_at_list_crown,
    get_skipped_fields,
    get_wild_extra_targets,
    has_collect_policy,
    strip_input_shape_fields,
    stub_code_gen_hook,
)
from .crown_definitions import InputNameLayout, InputNameLayoutRequest
from .fields import input_field_to_loc_map
from .shape_provider import provide_generic_resolved_shape


class ModelLoaderProvider(LoaderProvider):
    def __init__(
        self,
        *,
        name_sanitizer: NameSanitizer = NameSanitizer(),
        props: ModelLoaderProps = ModelLoaderProps(),
    ):
        self._name_sanitizer = name_sanitizer
        self._props = props

    def _provide_loader(self, mediator: Mediator, request: LoaderRequest) -> Loader:
        loader_gen = self._fetch_model_loader_gen(mediator, request)
        ctx_namespace = BuiltinContextNamespace()
        loader_code_builder = loader_gen.produce_code(ctx_namespace)

        try:
            code_gen_hook = mediator.delegating_provide(CodeGenHookRequest())
        except CannotProvide:
            code_gen_hook = stub_code_gen_hook

        return compile_closure_with_globals_capturing(
            compiler=self._get_compiler(),
            code_gen_hook=code_gen_hook,
            namespace=ctx_namespace.dict,
            body_builders=[loader_code_builder],
            closure_name=self._get_closure_name(request),
            closure_params='data',
            file_name=self._get_file_name(request),
        )

    def _fetch_model_loader_gen(self, mediator: Mediator, request: LoaderRequest) -> CodeGenerator:
        shape = self._fetch_shape(mediator, request)
        name_layout = self._fetch_name_layout(mediator, request, shape)
        shape = self._process_shape(shape, name_layout)
        self._validate_params(shape, name_layout)

        field_loaders = self._fetch_field_loaders(mediator, request, shape)
        strict_coercion = mediator.mandatory_provide(StrictCoercionRequest(loc_map=request.loc_map))
        debug_trail = mediator.mandatory_provide(DebugTrailRequest(loc_map=request.loc_map))
        return self._create_model_loader_gen(
            debug_trail=debug_trail,
            strict_coercion=strict_coercion,
            shape=shape,
            name_layout=name_layout,
            field_loaders=field_loaders,
            model_identity=self._fetch_model_identity(mediator, request, shape, name_layout),
        )

    def _fetch_model_identity(
        self,
        mediator: Mediator,
        request: LoaderRequest,
        shape: InputShape,
        name_layout: InputNameLayout,
    ) -> str:
        return (
            repr(request.loc_map[TypeHintLoc].type)
            if request.loc_map.has(TypeHintLoc) else
            repr(shape.constructor)
        )

    def _create_model_loader_gen(
        self,
        debug_trail: DebugTrail,
        strict_coercion: bool,
        shape: InputShape,
        name_layout: InputNameLayout,
        field_loaders: Mapping[str, Loader],
        model_identity: str,
    ) -> CodeGenerator:
        return ModelLoaderGen(
            shape=shape,
            name_layout=name_layout,
            debug_trail=debug_trail,
            strict_coercion=strict_coercion,
            field_loaders=field_loaders,
            model_identity=model_identity,
            props=self._props,
        )

    def _request_to_view_string(self, request: LoaderRequest) -> str:
        if request.loc_map.has(TypeHintLoc):
            tp = request.loc_map[TypeHintLoc].type
            if isinstance(tp, type):
                return tp.__name__
            return str(tp)
        return ''

    def _merge_view_string(self, *fragments: str) -> str:
        return '_'.join(filter(None, fragments))

    def _get_file_name(self, request: LoaderRequest) -> str:
        return self._merge_view_string(
            'model_loader', self._request_to_view_string(request),
        )

    def _get_closure_name(self, request: LoaderRequest) -> str:
        return self._merge_view_string(
            'model_loader', self._name_sanitizer.sanitize(self._request_to_view_string(request)),
        )

    def _get_compiler(self):
        return BasicClosureCompiler()

    def _fetch_shape(self, mediator: Mediator, request: LoaderRequest) -> InputShape:
        return provide_generic_resolved_shape(mediator, InputShapeRequest(loc_map=request.loc_map))

    def _fetch_name_layout(self, mediator: Mediator, request: LoaderRequest, shape: InputShape) -> InputNameLayout:
        return mediator.mandatory_provide(
            InputNameLayoutRequest(
                loc_map=request.loc_map,
                shape=shape,
            ),
            lambda x: 'Cannot create loader for model. Cannot fetch InputNameLayout',
        )

    def _fetch_field_loaders(
        self,
        mediator: Mediator,
        request: LoaderRequest,
        shape: InputShape,
    ) -> Mapping[str, Loader]:
        owner_type = request.loc_map[TypeHintLoc].type
        loaders = mediator.mandatory_provide_by_iterable(
            [
                LoaderRequest(loc_map=input_field_to_loc_map(owner_type, field))
                for field in shape.fields
            ],
            lambda: "Cannot create loader for model. Loaders for some fields cannot be created",
        )
        return {field.id: loader for field, loader in zip(shape.fields, loaders)}

    def _process_shape(self, shape: InputShape, name_layout: InputNameLayout) -> InputShape:
        wild_extra_targets = get_wild_extra_targets(shape, name_layout.extra_move)
        if wild_extra_targets:
            raise ValueError(
                f"ExtraTargets {wild_extra_targets} are attached to non-existing fields"
            )
        return strip_input_shape_fields(shape, get_skipped_fields(shape, name_layout))

    def _validate_params(self, processed_shape: InputShape, name_layout: InputNameLayout) -> None:
        if name_layout.extra_move is None and has_collect_policy(name_layout.crown):
            raise ValueError(
                "Cannot create loader that collect extra data"
                " if InputShape does not take extra data",
            )

        extra_targets_at_crown = get_extra_targets_at_crown(name_layout)
        if extra_targets_at_crown:
            raise ValueError(
                f"Extra targets {extra_targets_at_crown} are found at crown"
            )

        optional_fields_at_list_crown = get_optional_fields_at_list_crown(
            {field.id: field for field in processed_shape.fields},
            name_layout.crown,
        )
        if optional_fields_at_list_crown:
            raise ValueError(
                f"Optional fields {optional_fields_at_list_crown} are found at list crown"
            )


class InlinedShapeModelLoaderProvider(ModelLoaderProvider):
    def __init__(
        self,
        *,
        name_sanitizer: NameSanitizer = NameSanitizer(),
        props: ModelLoaderProps = ModelLoaderProps(),
        shape: InputShape,
    ):
        super().__init__(name_sanitizer=name_sanitizer, props=props)
        self._shape = shape

    def _fetch_shape(self, mediator: Mediator, request: LoaderRequest) -> InputShape:
        return self._shape
