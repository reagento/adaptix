#!/usr/bin/env python
# -*- coding: utf-8 -*-
from enum import Enum

from typing import List


def title(name: str) -> str:
    if len(name) < 2:
        return name.upper()
    return name[0].upper() + name[1:
                             ]


def split_name(name: str) -> List[str]:
    return name.split("_")


def snake(name):
    return "_".join(split_name(name))


def kebab(name):
    return "-".join(split_name(name))


def camel_lower(name):
    names = split_name(name)
    if len(names) < 2:
        return name
    return names[0] + "".join(title(x) for x in names[1:])


def camel(name):
    return "".join(title(x) for x in split_name(name))


class NamingPolicy(Enum):
    snake = "snake_case"
    kebab = "kebab-case"
    camel_lower = "camelCaseLower"
    camel = "CamelCase"


NAMING_FUNC = {
    NamingPolicy.snake: snake,
    NamingPolicy.kebab: kebab,
    NamingPolicy.camel_lower: camel_lower,
    NamingPolicy.camel: camel,
}


def convert_name(name: str, trim_trailing_underscore: bool = True, naming_policy: NamingPolicy = None) -> str:
    if naming_policy:
        name = NAMING_FUNC[naming_policy](name)
    if trim_trailing_underscore:
        name = name.rstrip("_")
    return name
