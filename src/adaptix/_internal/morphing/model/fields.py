from ...common import TypeHint
from ...model_tools.definitions import BaseField, InputField, OutputField
from ...provider.request_cls import FieldLoc, InputFieldLoc, LocMap, OutputFieldLoc, TypeHintLoc


def input_field_to_loc_map(owner_type: TypeHint, field: InputField) -> LocMap:
    return LocMap(
        TypeHintLoc(
            type=field.type,
        ),
        FieldLoc(
            owner_type=owner_type,
            field_id=field.id,
            default=field.default,
            metadata=field.metadata,
        ),
        InputFieldLoc(
            is_required=field.is_required,
        )
    )


def output_field_to_loc_map(owner_type: TypeHint, field: OutputField) -> LocMap:
    return LocMap(
        TypeHintLoc(
            type=field.type,
        ),
        FieldLoc(
            owner_type=owner_type,
            field_id=field.id,
            default=field.default,
            metadata=field.metadata,
        ),
        OutputFieldLoc(
            accessor=field.accessor,
        )
    )


def field_to_loc_map(owner_type: TypeHint, field: BaseField) -> LocMap:
    if isinstance(field, InputField):
        return input_field_to_loc_map(owner_type, field)
    if isinstance(field, OutputField):
        return output_field_to_loc_map(owner_type, field)
    raise TypeError
