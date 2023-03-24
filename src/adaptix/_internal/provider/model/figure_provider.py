import inspect
from dataclasses import replace
from typing import Any, Container, Generic, Iterable, Optional, TypeVar, Union, cast

from ...common import TypeHint
from ...model_tools import (
    DescriptorAccessor,
    IntrospectionImpossible,
    OutputField,
    OutputFigure,
    get_attrs_figure,
    get_class_init_figure,
    get_dataclass_figure,
    get_named_tuple_figure,
    get_typed_dict_figure,
)
from ...model_tools.definitions import FigureIntrospector, InputFigure
from ...type_tools.generic_resolver import GenericResolver, MembersStorage
from ..essential import CannotProvide, Mediator
from ..request_cls import LocatedRequest, TypeHintLoc
from ..static_provider import StaticProvider, static_provision_action
from .definitions import InputFigureRequest, OutputFigureRequest


class FigureProvider(StaticProvider):
    def __init__(self, introspector: FigureIntrospector):
        self._introspector = introspector

    @static_provision_action
    def _provide_input_figure(self, mediator: Mediator, request: InputFigureRequest) -> InputFigure:
        loc = request.loc_map.get_or_raise(TypeHintLoc, CannotProvide)

        try:
            figure = self._introspector(loc.type)
        except IntrospectionImpossible:
            raise CannotProvide

        if figure.input is None:
            raise CannotProvide

        return figure.input

    @static_provision_action
    def _provide_output_figure(self, mediator: Mediator, request: OutputFigureRequest) -> OutputFigure:
        loc = request.loc_map.get_or_raise(TypeHintLoc, CannotProvide)
        try:
            figure = self._introspector(loc.type)
        except IntrospectionImpossible:
            raise CannotProvide

        if figure.output is None:
            raise CannotProvide

        return figure.output


NAMED_TUPLE_FIGURE_PROVIDER = FigureProvider(get_named_tuple_figure)
TYPED_DICT_FIGURE_PROVIDER = FigureProvider(get_typed_dict_figure)
DATACLASS_FIGURE_PROVIDER = FigureProvider(get_dataclass_figure)
CLASS_INIT_FIGURE_PROVIDER = FigureProvider(get_class_init_figure)
ATTRS_FIGURE_PROVIDER = FigureProvider(get_attrs_figure)


class PropertyAdder(StaticProvider):
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
    def _provide_output_figure(self, mediator: Mediator[OutputFigure], request: OutputFigureRequest) -> OutputFigure:
        tp = request.loc_map.get_or_raise(TypeHintLoc, CannotProvide).type
        figure = mediator.provide_from_next()

        additional_fields = tuple(
            replace(field, type=self._infer_property_type(tp, self._get_attr_name(field)))
            if field.name in self._infer_types_for else
            field
            for field in self._output_fields
        )
        return replace(figure, fields=figure.fields + additional_fields)

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


Fig = TypeVar('Fig', bound=Union[InputFigure, OutputFigure])


class FigureGenericResolver(Generic[Fig]):
    def __init__(self, mediator: Mediator, initial_request: LocatedRequest[Fig]):
        self._mediator = mediator
        self._initial_request = initial_request

    def provide(self) -> Fig:
        resolver = GenericResolver(self._get_members)
        members_storage = resolver.get_resolved_members(
            self._initial_request.loc_map[TypeHintLoc].type
        )
        if members_storage.meta is None:
            raise CannotProvide
        return replace(
            members_storage.meta,
            fields=tuple(
                replace(fld, type=members_storage.members[fld.name])
                for fld in members_storage.meta.fields
            )
        )

    def _get_members(self, tp) -> MembersStorage[str, Optional[Fig]]:
        try:
            figure = self._mediator.provide(
                replace(
                    self._initial_request,
                    loc_map=self._initial_request.loc_map.add(TypeHintLoc(type=tp)),
                )
            )
        except CannotProvide:
            return MembersStorage(
                meta=None,
                members={},
                overriden=frozenset(),
            )
        return MembersStorage(
            meta=figure,
            members={field.name: field.type for field in figure.fields},
            overriden=figure.overriden_types,
        )


def provide_generic_resolved_figure(mediator: Mediator, request: LocatedRequest[Fig]) -> Fig:
    if not request.loc_map.has(TypeHintLoc):
        return mediator.provide(request)
    return FigureGenericResolver(mediator, request).provide()
