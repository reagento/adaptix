from enum import Enum
from typing import List, Optional, Union

from .path_utils import CleanKey, CleanPath, NameMapping, replace_ellipsis


def split_by_underscore(s: str) -> List[str]:
    return s.split("_")


def is_snake_case(name: str) -> bool:
    return name.lower() == name


def snake(snake_name):
    return snake_name


def upper_snake(snake_name):
    return snake_name.upper()


def kebab(snake_name):
    return "-".join(split_by_underscore(snake_name))


def lower(snake_name: str):
    return snake_name.replace("_", "").lower()


def upper(snake_name):
    return snake_name.replace("_", "").upper()


def camel_lower(snake_name):
    names = split_by_underscore(snake_name)
    return f"{names[0].lower()}{''.join(x.title() for x in names[1:])}"


def camel(snake_name):
    return "".join(x.title() for x in split_by_underscore(snake_name))


def camel_snake(snake_name):
    return "_".join(x.title() for x in split_by_underscore(snake_name))


def dot(snake_name):
    return ".".join(split_by_underscore(snake_name)).lower()


def camel_dot(snake_name):
    return ".".join(x.title() for x in split_by_underscore(snake_name))


def upper_dot(snake_name):
    return ".".join(x.upper() for x in split_by_underscore(snake_name))


class NameStyle(Enum):
    """
    Enumeration to describe which styles do field names fit
    in plain (serialized/unparsed) structure
    """
    ignore = "ignore"
    snake = "snake_case"
    kebab = "kebab-case"
    camel_lower = "camelCaseLower"
    camel = "CamelCase"
    lower = "lowercase"
    upper = "UPPERCASE"
    upper_snake = "UPPER_SNAKE_CASE"
    camel_snake = "Camel_Snake"
    dot = "dot.case"
    camel_dot = "Camel.Dot"
    upper_dot = "UPPER.DOT"


CONVERTING_FUNC = {
    NameStyle.snake: snake,
    NameStyle.kebab: kebab,
    NameStyle.camel_lower: camel_lower,
    NameStyle.camel: camel,
    NameStyle.lower: lower,
    NameStyle.upper: upper,
    NameStyle.upper_snake: upper_snake,
    NameStyle.camel_snake: camel_snake,
    NameStyle.dot: dot,
    NameStyle.camel_dot: camel_dot,
    NameStyle.upper_dot: upper_dot,
}


def convert_name_simple(
        name: str,
        name_style: Optional[NameStyle],
        trim_trailing_underscore: Optional[bool],
) -> str:
    if name_style is None:
        name_style = NameStyle.ignore
    if trim_trailing_underscore:
        name = name.rstrip("_")
    if name_style is not NameStyle.ignore:
        if not is_snake_case(name):
            raise ValueError("cannot convert python name that not follow snake_case")
        name = CONVERTING_FUNC[name_style](name)
    return name


def convert_name(
        name: str,
        name_style: Optional[NameStyle],
        name_mapping: NameMapping,
        trim_trailing_underscore: Optional[bool],
) -> Union[CleanKey, CleanPath]:
    if name_mapping:
        if name in name_mapping:
            return replace_ellipsis(name, name_mapping[name])
        if Ellipsis in name_mapping:  # `...` used as dict key
            new_name = convert_name_simple(name, name_style, trim_trailing_underscore)
            return replace_ellipsis(new_name, name_mapping[Ellipsis])
    return convert_name_simple(name, name_style, trim_trailing_underscore)
