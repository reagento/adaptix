from ...model_tools.definitions import BaseField, InputField, OutputField
from ..request_cls import FieldLoc, InputFieldLoc, LocMap, OutputFieldLoc, TypeHintLoc


def input_field_to_loc_map(field: InputField) -> LocMap:
    return LocMap(
        TypeHintLoc(
            type=field.type,
        ),
        FieldLoc(
            name=field.id,
            default=field.default,
            metadata=field.metadata,
        ),
        InputFieldLoc(
            is_required=field.is_required,
            param_kind=field.param_kind,
            param_name=field.param_name,
        )
    )


def output_field_to_loc_map(field: OutputField) -> LocMap:
    return LocMap(
        TypeHintLoc(
            type=field.type,
        ),
        FieldLoc(
            name=field.id,
            default=field.default,
            metadata=field.metadata,
        ),
        OutputFieldLoc(
            accessor=field.accessor,
        )
    )


def field_to_loc_map(field: BaseField) -> LocMap:
    if isinstance(field, InputField):
        return input_field_to_loc_map(field)
    if isinstance(field, OutputField):
        return output_field_to_loc_map(field)
    raise TypeError
