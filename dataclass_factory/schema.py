from dataclasses import dataclass, asdict, fields

from typing import List, Dict, Callable, Tuple, Any, Type, Sequence

from .common import Serializer, Parser
from .naming import NameStyle, NAMING_FUNC

FieldMapper = Callable[[str], Tuple[str, bool]]
SimpleFieldMapping = Dict[str, str]
Validator = Callable[[Any], bool]


@dataclass
class Schema:
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
