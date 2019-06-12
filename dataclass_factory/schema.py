from copy import copy
from dataclasses import dataclass, asdict, fields

from typing import List, Dict, Callable, Tuple, Type, Sequence, Optional

from .common import Serializer, Parser
from .naming import NameStyle, NAMING_FUNC

FieldMapper = Callable[[str], Tuple[str, bool]]
SimpleFieldMapping = Dict[str, str]


@dataclass
class Schema:
    only: Optional[List[str]] = None
    exclude: Optional[List[str]] = None
    name_mapping: Optional[Dict[str, str]] = None
    only_mapped: Optional[bool] = None

    name_style: Optional[NameStyle] = None
    trim_trailing_underscore: Optional[bool] = None
    skip_internal: Optional[bool] = None

    serializer: Optional[Serializer] = None
    parser: Optional[Parser] = None


def merge_schema(schema: Optional[Schema], default: Optional[Schema]) -> Schema:
    if schema is None:
        return default or Schema()
    if default is None:
        return copy(schema)
    default_dict = asdict(default)
    return Schema(**{
        k: default_dict[k] if v is None else v
        for k, v in asdict(schema).items()
    })


def convert_name(
        name: str,
        name_style: Optional[NameStyle],
        name_mapping: Optional[Dict[str, str]],
        trim_trailing_underscore: Optional[bool]
):
    if name_mapping and name in name_mapping:
        return name_mapping[name]
    if trim_trailing_underscore:
        name = name.rstrip("_")
    if name_style:
        name = NAMING_FUNC[name_style](name)
    return name


def get_dataclass_fields(schema: Schema, class_: Type) -> Sequence[Tuple[str, str]]:
    only_mapped = schema.only_mapped and schema.only is None
    all_fields = {
        f.name
        for f in fields(class_)
        if (schema.only is None or f.name in schema.only) and
           (schema.exclude is None or f.name not in schema.exclude)
    }
    if only_mapped:
        if schema.name_mapping is None:
            raise ValueError("`name_mapping` is None, and `only_mapped` is True")
        return tuple(
            (k, v)
            for k, v in schema.name_mapping.items()
            if k in all_fields
        )
    return tuple(
        (k, convert_name(k, schema.name_style, schema.name_mapping, schema.trim_trailing_underscore))
        for k in all_fields
        if (schema.name_mapping is not None and k in schema.name_mapping) or
        (schema.only is not None and k in schema.only) or
        not (schema.skip_internal and k.startswith("_"))
    )
