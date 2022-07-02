from typing import Any, Callable, Optional

from .definitions import (
    InputFigure, OutputFigure,
    InputFigureRequest, OutputFigureRequest,
)
from ..essential import Mediator, CannotProvide, Provider, Request
from ...model_tools import (
    get_named_tuple_input_figure, get_named_tuple_output_figure,
    get_typed_dict_input_figure, get_typed_dict_output_figure,
    get_dataclass_input_figure, get_dataclass_output_figure,
    get_class_init_input_figure, IntrospectionError,
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
