from dataclasses import dataclass, asdict, fields

from typing import List, Dict, Callable, Tuple, Any, Type, Sequence

from .common import Serializer, Parser
from .naming import NameStyle, NAMING_FUNC

FieldMapper = Callable[[str], Tuple[str, bool]]
SimpleFieldMapping = Dict[str, str]


@dataclass
class Schema:
    only: List[str] = None
    exclude: List[str] = None
    name_mapping: Dict[str, str] = None
    only_mapped: bool = None

    name_style: NameStyle = None
    trim_trailing_underscore: bool = None
    skip_internal: bool = None

    serializer: Serializer = None
    parser: Parser = None


def merge_schema(schema: Schema, default: Schema) -> Schema:
    if schema is None:
        return default
    default_dict = asdict(default)
    return Schema(**{
        k: default_dict[k] if v is None else v
        for k, v in asdict(schema).items()
    })


def convert_name(name, name_style: NameStyle, name_mapping: Dict[str, str], trim_trailing_underscore: bool):
    if name_mapping and name in name_mapping:
        return name_mapping[name]
    if trim_trailing_underscore:
        name = name.rstrip("_")
    if name_style:
        name = NAMING_FUNC[name_style](name)
    return name


def get_dataclass_fields(schema: Schema, class_: Type) -> Sequence[Tuple[str, str]]:
    all_fields = {
        f.name
        for f in fields(class_)
        if (schema.only is None or f.name in schema.only) and
           (schema.exclude is None or f.name not in schema.exclude)
    }
    if schema.only_mapped:
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
