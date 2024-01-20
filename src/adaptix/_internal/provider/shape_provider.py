import inspect
from dataclasses import dataclass, replace
from typing import Any, Container, Generic, Iterable, Optional, TypeVar, Union, cast

from ..common import TypeHint
from ..model_tools.definitions import (
    DescriptorAccessor,
    InputShape,
    IntrospectionImpossible,
    OutputField,
    OutputShape,
    ShapeIntrospector,
)
from ..model_tools.introspection.attrs import get_attrs_shape
from ..model_tools.introspection.class_init import get_class_init_shape
from ..model_tools.introspection.dataclass import get_dataclass_shape
from ..model_tools.introspection.named_tuple import get_named_tuple_shape
from ..model_tools.introspection.typed_dict import get_typed_dict_shape
from ..provider.essential import CannotProvide, Mediator
from ..provider.loc_stack_filtering import create_loc_stack_checker
from ..type_tools.generic_resolver import GenericResolver, MembersStorage
from .provider_template import ProviderWithAttachableLSC
from .request_cls import LocatedRequest, TypeHintLoc
from .static_provider import StaticProvider, static_provision_action


@dataclass(frozen=True)
class InputShapeRequest(LocatedRequest[InputShape]):
    pass


@dataclass(frozen=True)
class OutputShapeRequest(LocatedRequest[OutputShape]):
    pass


class ShapeProvider(StaticProvider):
    def __init__(self, introspector: ShapeIntrospector):
        self._introspector = introspector

    @static_provision_action
    def _provide_input_shape(self, mediator: Mediator, request: InputShapeRequest) -> InputShape:
        loc = request.last_map.get_or_raise(TypeHintLoc, CannotProvide)
        try:
            shape = self._introspector(loc.type)
        except IntrospectionImpossible:
            raise CannotProvide

        if shape.input is None:
            raise CannotProvide

        return shape.input

    @static_provision_action
    def _provide_output_shape(self, mediator: Mediator, request: OutputShapeRequest) -> OutputShape:
        loc = request.last_map.get_or_raise(TypeHintLoc, CannotProvide)
        try:
            shape = self._introspector(loc.type)
        except IntrospectionImpossible:
            raise CannotProvide

        if shape.output is None:
            raise CannotProvide

        return shape.output


NAMED_TUPLE_SHAPE_PROVIDER = ShapeProvider(get_named_tuple_shape)
TYPED_DICT_SHAPE_PROVIDER = ShapeProvider(get_typed_dict_shape)
DATACLASS_SHAPE_PROVIDER = ShapeProvider(get_dataclass_shape)
CLASS_INIT_SHAPE_PROVIDER = ShapeProvider(get_class_init_shape)
ATTRS_SHAPE_PROVIDER = ShapeProvider(get_attrs_shape)


class PropertyExtender(StaticProvider):
    def __init__(
        self,
        output_fields: Iterable[OutputField],
        infer_types_for: Container[str],
    ):
        self._output_fields = output_fields
        self._infer_types_for = infer_types_for

        bad_fields_accessors = [
            field for field in self._output_fields if not isinstance(field.accessor, DescriptorAccessor)
        ]
        if bad_fields_accessors:
            raise ValueError(
                f"Fields {bad_fields_accessors} has bad accessors,"
                f" all fields must use DescriptorAccessor"
            )

    @static_provision_action
    def _provide_output_shape(self, mediator: Mediator[OutputShape], request: OutputShapeRequest) -> OutputShape:
        tp = request.last_map.get_or_raise(TypeHintLoc, CannotProvide).type
        shape = mediator.provide_from_next()

        additional_fields = tuple(
            replace(field, type=self._infer_property_type(tp, self._get_attr_name(field)))
            if field.id in self._infer_types_for else
            field
            for field in self._output_fields
        )
        return replace(shape, fields=shape.fields + additional_fields)

    def _get_attr_name(self, field: OutputField) -> str:
        return cast(DescriptorAccessor, field.accessor).attr_name

    def _infer_property_type(self, tp: TypeHint, attr_name: str) -> TypeHint:
        prop = getattr(tp, attr_name)

        if not isinstance(prop, property):
            raise CannotProvide

        if prop.fget is None:
            raise CannotProvide

        signature = inspect.signature(prop.fget)

        if signature.return_annotation is inspect.Signature.empty:
            return Any
        return signature.return_annotation


ShapeT = TypeVar('ShapeT', bound=Union[InputShape, OutputShape])


class ShapeGenericResolver(Generic[ShapeT]):
    def __init__(self, mediator: Mediator, initial_request: LocatedRequest[ShapeT]):
        self._mediator = mediator
        self._initial_request = initial_request

    def provide(self) -> ShapeT:
        resolver = GenericResolver(self._get_members)
        members_storage = resolver.get_resolved_members(
            self._initial_request.last_map[TypeHintLoc].type
        )
        if members_storage.meta is None:
            raise CannotProvide
        return replace(
            members_storage.meta,
            fields=tuple(  # type: ignore[arg-type]
                replace(fld, type=members_storage.members[fld.id])
                for fld in members_storage.meta.fields
            )
        )

    def _get_members(self, tp) -> MembersStorage[str, Optional[ShapeT]]:
        try:
            shape = self._mediator.delegating_provide(
                replace(
                    self._initial_request,
                    loc_stack=self._initial_request.loc_stack.add_to_last_map(TypeHintLoc(type=tp)),
                )
            )
        except CannotProvide:
            return MembersStorage(
                meta=None,
                members={},
                overriden=frozenset(),
            )
        return MembersStorage(
            meta=shape,
            members={field.id: field.type for field in shape.fields},
            overriden=shape.overriden_types,
        )


def provide_generic_resolved_shape(mediator: Mediator, request: LocatedRequest[ShapeT]) -> ShapeT:
    if not request.last_map.has(TypeHintLoc):
        return mediator.delegating_provide(request)
    return ShapeGenericResolver(mediator, request).provide()


T = TypeVar('T')


class SimilarShapeProvider(ProviderWithAttachableLSC):
    def __init__(self, target: TypeHint, prototype: TypeHint, for_input: bool = True, for_output: bool = True):
        self._target = target
        self._prototype = prototype
        self._loc_stack_checker = create_loc_stack_checker(self._target)
        self._for_input = for_input
        self._for_output = for_output

    @static_provision_action
    def _provide_input_shape(self, mediator: Mediator, request: InputShapeRequest) -> InputShape:
        if not self._for_input:
            raise CannotProvide

        self._apply_loc_stack_checker(mediator, request)
        shape = mediator.delegating_provide(
            replace(
                request,
                loc_stack=request.loc_stack.add_to_last_map(TypeHintLoc(self._prototype)),
            )
        )
        return replace(shape, constructor=self._target)

    @static_provision_action
    def _provide_output_shape(self, mediator: Mediator, request: OutputShapeRequest) -> OutputShape:
        if not self._for_output:
            raise CannotProvide

        self._apply_loc_stack_checker(mediator, request)
        shape = mediator.delegating_provide(
            replace(
                request,
                loc_stack=request.loc_stack.add_to_last_map(TypeHintLoc(self._prototype)),
            )
        )
        return shape
