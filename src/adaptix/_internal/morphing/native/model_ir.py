from adaptix._internal.morphing.model.crown_definitions import InpDictCrown, InpFieldCrown
from adaptix._internal.morphing.native.bytecodes import CheckType, ConvertField, FieldBlock, FieldOperation, ReadField
from adaptix._internal.morphing.native.plan import ModelLoaderPlan
from adaptix._internal.morphing.native.registry import identity_spec


def build_model_fields(plan: ModelLoaderPlan) -> FieldBlock:
    crown = plan.name_layout.crown
    if not isinstance(crown, InpDictCrown):
        raise TypeError("Field IR requires a flat dictionary crown")
    operations: list[FieldOperation] = []
    required_keys = set()
    for index, (key, child) in enumerate(crown.map.items()):
        if not isinstance(child, InpFieldCrown):
            raise TypeError("Field IR requires a flat dictionary crown")
        field = plan.shape.fields_dict[child.id]
        operations.append(ReadField(field.id, key, field.is_required, index))
        if field.is_required:
            required_keys.add(key)
        converter = plan.field_loaders[field.id]
        spec = identity_spec(converter)
        if spec is None:
            operations.append(ConvertField(field.id, converter, (key,)))
        else:
            types, nullable = spec
            if types or nullable:
                operations.append(CheckType(field.id, (*types, type(None)) if nullable else types, converter, (key,)))
    return FieldBlock(tuple(operations), frozenset(required_keys))
