from dataclasses import dataclass, asdict, fields

from typing import List, Dict, Callable, Tuple, Any, Type, Sequence

from .common import Serializer, Parser
from .naming import NameStyle, convert_name

FieldMapper = Callable[[str], Tuple[str, bool]]
SimpleFieldMapping = Dict[str, str]
Validator = Callable[[Any], bool]


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
    validator: Validator = None


def merge_schema(schema: Schema, default: Schema) -> Schema:
    if schema is None:
        return default
    default_dict = asdict(default)
    return Schema(**{
        k: default_dict[k] if v is None else v
        for k, v in asdict(schema).items()
    })


def convert_name_ex(name, name_style: NameStyle, name_mapping: Dict[str, str], trim_trailing_underscore: bool):
    if name in name_mapping:
        return name_mapping[name]
    return convert_name(name, trim_trailing_underscore, name_style)


def get_dataclass_fields(schema: Schema, default_schema: Schema, class_: Type) -> Sequence[Tuple[str, str]]:
    schema = merge_schema(schema, default_schema)

    all_fields = {
        f.name: f
        for f in fields(class_)
        if (f.name in schema.only or schema.only is None) and
           (f.name not in schema.exclude or schema.exclude is None)
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
        (k, convert_name_ex(k, schema.name_style, schema.name_mapping, schema.trim_trailing_underscore))
        for k in all_fields
        if (schema.name_mapping is not None and k in schema.name_mapping) or
        (schema.only is not None and k in schema.only) or
        not (schema.skip_internal and k.endswith("_"))
    )


DEFAULT_SCHEMA = Schema(
    trim_trailing_underscore=True,
    skip_internal=True,
    only_mapped=False,
)


class Factory:
    def __init__(self,
                 default_schema: Schema = None,
                 schemas: Dict[Type, Schema] = None,
                 debug_path: bool = False):
        self.default_schema = merge_schema(default_schema, DEFAULT_SCHEMA)
        self.schemas = schemas
        self.debug_path = debug_path
        self.schemas = {
            type_: merge_schema(schema, self.default_schema)
            for type_, schema in schemas.items()
        }

    def parser(self, class_: Type) -> Parser:
        pass

    def serializer(self, class_: Type) -> Serializer:
        pass


"""
`only_mapped` - исключает из обработки все поля кроме указанных в `names_mapping`
`skip_internal` - исключить поля с префиксом _ (применяется если поле не указано в only и names_mapping)
`only` - включить только определенные поля. Более высокий приоритет чем names_mapping с укзаанным only_mapped и `skip_internal`
`exclude_fields` - исключить определенные поля. Более высоки приоритет чем `only`

`names_mapping` - сответствие между именами в датаклассе (ключи) и в получаемом словаре. В виде словаря или функции
`name_style` - конвертация стилей имен для полей, не укзазанных в names_mapping
`trim_trainling_underscore` - обрезка конечного _ для всех полей, кроме указанных в names_mapping

`serializer` - функция для преобрзаования ИЗ типа
`parser` - функция преобразования В тип
"""
