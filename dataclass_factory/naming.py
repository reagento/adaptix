from enum import Enum

from typing import List, Optional, Dict, Union

from .path_utils import Path


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


def convert_name(
        name: str,
        name_style: Optional[NameStyle],
        name_mapping: Optional[Dict[str, Union[str, Path]]],
        trim_trailing_underscore: Optional[bool]
) -> Union[str, Path]:
    if name_mapping and name in name_mapping:
        return name_mapping[name]
    if not is_snake_case(name):
        raise ValueError("can not convert python name that not follow snake_case")
    if trim_trailing_underscore:
        name = name.rstrip("_")
    if name_style:
        name = CONVERTING_FUNC[name_style](name)
    return name
