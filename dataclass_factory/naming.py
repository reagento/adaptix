#!/usr/bin/env python
# -*- coding: utf-8 -*-
from enum import Enum

from typing import List


def title(name: str) -> str:
    if len(name) < 2:
        return name.upper()
    return name[0].upper() + name[1:]


def split_name(name: str) -> List[str]:
    return name.split("_")


def snake(name):
    return "_".join(split_name(name))


def kebab(name):
    return "-".join(split_name(name))


def lower(name):
    return "".join(split_name(name))


def upper(name):
    return "".join(split_name(name)).upper()


def upper_snake(name):
    return "_".join(split_name(name)).upper()


def camel_lower(name):
    names = split_name(name)
    if len(names) < 2:
        return name
    return names[0] + "".join(title(x) for x in names[1:])


def camel(name):
    return "".join(title(x) for x in split_name(name))


def camel_snake(name):
    return "_".join(title(x) for x in split_name(name))


def dot(name):
    return ".".join(split_name(name))


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


NAMING_FUNC = {
    NameStyle.snake: snake,
    NameStyle.kebab: kebab,
    NameStyle.camel_lower: camel_lower,
    NameStyle.camel: camel,
    NameStyle.lower: lower,
    NameStyle.upper: upper,
    NameStyle.upper_snake: upper_snake,
    NameStyle.camel_snake: camel_snake,
    NameStyle.dot: dot,
}
