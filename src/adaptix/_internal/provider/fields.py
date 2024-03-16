from typing import Union

from ..model_tools.definitions import BaseField, InputField, OutputField
from .request_cls import FieldLoc, InputFieldLoc, OutputFieldLoc


def input_field_to_loc_map(field: InputField) -> InputFieldLoc:
    return InputFieldLoc(
        type=field.type,
        field_id=field.id,
        default=field.default,
        metadata=field.metadata,
        is_required=field.is_required,
    )


def output_field_to_loc_map(field: OutputField) -> OutputFieldLoc:
    return OutputFieldLoc(
        type=field.type,
        field_id=field.id,
        default=field.default,
        metadata=field.metadata,
        accessor=field.accessor,
    )


def base_field_to_loc_map(field: BaseField) -> FieldLoc:
    return FieldLoc(
        type=field.type,
        field_id=field.id,
        default=field.default,
        metadata=field.metadata,
    )


def field_to_loc_map(field: BaseField) -> Union[FieldLoc, InputFieldLoc, OutputFieldLoc]:
    if isinstance(field, InputField):
        return input_field_to_loc_map(field)
    if isinstance(field, OutputField):
        return output_field_to_loc_map(field)
    return base_field_to_loc_map(field)
