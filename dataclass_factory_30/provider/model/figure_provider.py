import inspect
from dataclasses import replace
from typing import Any, Callable, Optional, Iterable, Container, cast

from .definitions import (
    InputFigureRequest, OutputFigureRequest,
)
from ..essential import Mediator, CannotProvide, Provider, Request
from ..static_provider import StaticProvider, static_provision_action
from ...common import TypeHint
from ...model_tools import (
    InputFigure, OutputFigure,
    get_named_tuple_input_figure, get_named_tuple_output_figure,
    get_typed_dict_input_figure, get_typed_dict_output_figure,
    get_dataclass_input_figure, get_dataclass_output_figure,
    get_class_init_input_figure, IntrospectionError,
    OutputField, DescriptorAccessor,
)


class FigureProvider(Provider):
    def __init__(
        self,
        input_figure_getter: Optional[Callable[[Any], InputFigure]] = None,
        output_figure_getter: Optional[Callable[[Any], OutputFigure]] = None,
    ):
        self._input_figure_getter = input_figure_getter
        self._output_figure_getter = output_figure_getter

    def apply_provider(self, mediator: Mediator, request: Request):
        if isinstance(request, InputFigureRequest):
            if self._input_figure_getter is None:
                raise CannotProvide
            try:
                return self._input_figure_getter(request.type)
            except IntrospectionError:
                raise CannotProvide

        if isinstance(request, OutputFigureRequest):
            if self._output_figure_getter is None:
                raise CannotProvide
            try:
                return self._output_figure_getter(request.type)
            except IntrospectionError:
                raise CannotProvide

        raise CannotProvide


NAMED_TUPLE_FIGURE_PROVIDER = FigureProvider(
    get_named_tuple_input_figure,
    get_named_tuple_output_figure,
)

TYPED_DICT_FIGURE_PROVIDER = FigureProvider(
    get_typed_dict_input_figure,
    get_typed_dict_output_figure,
)

DATACLASS_FIGURE_PROVIDER = FigureProvider(
    get_dataclass_input_figure,
    get_dataclass_output_figure,
)

CLASS_INIT_FIGURE_PROVIDER = FigureProvider(
    get_class_init_input_figure,
)


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
    def provide_output_figure(self, mediator: Mediator, request: OutputFigureRequest) -> OutputFigure:
        figure: OutputFigure = mediator.provide_from_next(request)

        additional_fields = tuple(
            replace(field, type=self._infer_property_type(request.type, self._get_attr_name(field)))
            if field.name in self._infer_types_for else
            field
            for field in self._output_fields
        )

        return replace(figure, fields=figure.fields + additional_fields)

    def _get_attr_name(self, field: OutputField) -> str:
        return cast(DescriptorAccessor, field.accessor).attr_name

    def _infer_property_type(self, tp: TypeHint, attr_name: str):
        if not isinstance(tp, type):
            raise CannotProvide

        prop = getattr(tp, attr_name)

        if not isinstance(prop, property):
            raise CannotProvide

        if prop.fget is None:
            raise CannotProvide

        signature = inspect.signature(prop.fget)

        if signature.return_annotation is inspect.Signature.empty:
            return Any
        return signature.return_annotation
