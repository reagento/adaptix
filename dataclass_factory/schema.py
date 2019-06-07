from dataclasses import dataclass, field
from typing import List, Dict, Sequence, Callable, Tuple, Union

from .common import Serializer, Parser
from .naming import NameStyle

FieldMapper = Callable[[str], Tuple[str, bool]]
SimpleFieldMapping = Dict[str, str]


@dataclass
class Schema:
    name_style: NameStyle = None
    excluded_fields: Sequence[str] = field(default_factory=tuple)
    fields: List[str] = None
    only_mapped: bool = True
    skip_internal: bool = None
    trim_trainling_underscore: bool = None
    serializer: Serializer = None
    parser: Parser = None
    names_mapping: Union[SimpleFieldMapping, FieldMapper] = None


"""
`only_mapped` - исключает из обработки все поля кроме указанных в `names_mapping`
`skip_internal` - исключить поля с префиксом _
`fields` - включить только определенные поля. Более высокий приоритет чем names_mapping с укзаанным only_mapped и `skip_internal`
`exclude_fields` - исключить определенные поля. Более высоки приоритет чем `fields`

`names_mapping` - сответствие между именами в датаклассе (ключи) и в получаемом словаре. В виде словаря или функции
`name_style` - конвертация стилей имен для полей, не укзазанных в names_mapping
`trim_trainling_underscore` - обрезка конечного _ для всех полей, кроме указанных в names_mapping

`serializer` - функция для преобрзаования ИЗ типа
`parser` - функция преобразования В тип
"""
