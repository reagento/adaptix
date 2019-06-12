#!/usr/bin/env python
# -*- coding: utf-8 -*-
from enum import Enum

from typing import Dict, Callable


def _prepare_value(value, type_serializers: Dict[type, Callable] = None):
    if type_serializers and (type(value)) in type_serializers:
        return type_serializers[type(value)](value)
    if isinstance(value, Enum):
        return value.value
    return value


def dict_factory(trim_trailing_underscore=True, skip_none=False, skip_internal=False,
                 type_serializers: Dict[type, Callable] = None):
    """
    Формируем словарь с данными из dataclass со следующими ограничениями:
      1. Пропускаем все элементы, которые назваются с первого символа `_` - это внутренние свойства
      2. отрезаем конечный символ `_`, так как он используется только для исключения конфликта
          с ключевыми словами и встроенными функциями python
      3. Пропускаются None значения
    """

    def impl(data):
        return {
            (k.rstrip("_") if trim_trailing_underscore else k): _prepare_value(v, type_serializers=type_serializers)
            for k, v in data
            if not (k.startswith("_") and skip_internal) and (v is not None or not skip_none)
        }

    return impl
