#!/usr/bin/env python
# -*- coding: utf-8 -*-
import inspect
from collections import deque
from dataclasses import is_dataclass, fields, Field
from enum import Enum
from typing import ClassVar, Any, Collection, Optional, List, Set, Tuple, FrozenSet, Deque, Dict, T, KT, VT


def _hasargs(type_, *args):
    try:
        if not type_.__args__:
            return False
        res = all(arg in type_.__args__ for arg in args)
    except AttributeError:
        return False
    else:
        return res


def _issubclass_safe(cls, classinfo):
    try:
        result = issubclass(cls, classinfo)
    except Exception:
        return False
    else:
        return result


def _is_tuple(type_) -> bool:
    try:
        # __origin__ exists in 3.7 on user defined generics
        return _issubclass_safe(type_.__origin__, Tuple) or _issubclass_safe(type_, Tuple)
    except AttributeError:
        return False


def _is_collection(type_) -> bool:
    try:
        # __origin__ exists in 3.7 on user defined generics
        return _issubclass_safe(type_.__origin__, Collection) or _issubclass_safe(type_, Collection)
    except AttributeError:
        return False


def _is_optional(type_) -> bool:
    return _issubclass_safe(type_, Optional) or _hasargs(type_, type(None))


def _is_union(type_: ClassVar) -> bool:
    try:
        return bool(type_.__args__)
    except:
        return False


def get_collection_factory(cls):
    origin = cls.__origin__ or cls
    res = {
        List: list,
        list: list,
        Set: set,
        set: set,
        Tuple: tuple,
        tuple: tuple,
        FrozenSet: frozenset,
        frozenset: frozenset,
        Deque: deque,
        deque: deque
    }.get(origin)
    if not res:
        raise NotImplementedError("Class %s not supported" % cls)
    return res


def _is_dict(cls):
    try:
        origin = cls.__origin__ or cls
        return origin in (dict, Dict)
    except AttributeError:
        return False


def parse(data: Any, cls: ClassVar, trim_trailing_underscore=True):
    """
    * Создание класса данных из словаря
    * Примитивы проверяются на соответствие типов
    * Из коллекций поддерживается list и tuple
    * При парсинге Union ищет первый подходящий тип
    """
    if is_dataclass(cls):
        parsed: dict = {}
        field: Field
        for field in fields(cls):
            if trim_trailing_underscore:
                name = field.name.rstrip("_")
            else:
                name = field.name
            if field.init:
                if name in data:
                    parsed[field.name] = parse(data[name], field.type)
        return cls(**parsed)

    if _is_optional(cls) and data is None:
        return None
    elif _is_dict(cls):
        key_type_arg = cls.__args__[0] if cls.__args__ else Any
        value_type_arg = cls.__args__[1] if cls.__args__ else Any
        return {
            parse(k, key_type_arg, trim_trailing_underscore=trim_trailing_underscore):
                parse(v, value_type_arg, trim_trailing_underscore=trim_trailing_underscore)
            for k, v in data.items()
        }
    elif _is_collection(cls) and not isinstance(data, str) and not isinstance(data, bytes):
        if _is_tuple(cls):
            if not _hasargs(cls):
                return tuple(parse(x, Any) for x in data)
            if len(cls.__args__) == 2 and cls.__args__[1] is Ellipsis:
                return tuple(parse(x, cls.__args__[0]) for x in data)
            elif len(cls.__args__) != len(data):
                raise ValueError("Length of data (%s) != length of types (%s)" % (len(data), len(cls.__args__)))
            else:
                return tuple(parse(x, cls.__args__[i]) for i, x in enumerate(data))
        else:
            collection_factory = get_collection_factory(cls)
            type_arg = cls.__args__[0] if cls.__args__ else Any
            return collection_factory(
                parse(x, type_arg, trim_trailing_underscore=trim_trailing_underscore) for x in data
            )
    elif _is_union(cls):
        for t in cls.__args__:
            if t is not None:
                try:
                    return parse(data, t, trim_trailing_underscore=trim_trailing_underscore)
                except ValueError:
                    pass  # ignore value error as it is union
                except TypeError:
                    pass  # ignore type error as it is union
        raise ValueError("Cannot parse `%s` as any of `%s`" % (data, cls.__args__))
    elif cls in (Any, T, KT, VT, inspect._empty):
        return data
    elif _issubclass_safe(cls, Enum):
        return cls(data)
    elif _issubclass_safe(cls, str) and isinstance(data, str):
        return data
    elif _issubclass_safe(cls, bool) and isinstance(data, bool):
        return data
    elif _issubclass_safe(cls, int) and isinstance(data, int):
        return data
    elif _issubclass_safe(cls, float) and (isinstance(data, float) or isinstance(data, int)):
        return float(data)
    elif _issubclass_safe(cls, complex) and (
            isinstance(data, float) or isinstance(data, int) or isinstance(data, complex)):
        return complex(data)
    else:
        try:
            arguments = inspect.signature(cls.__init__).parameters
            res = {}
            for k, v in arguments.items():
                if k != "self":
                    res[k] = parse(data.get(k), v.annotation)
            return cls(**res)
        except AttributeError as e:
            raise ValueError("Unknown type `%s` or invalid data: %s" % (cls, repr(data)))


def _prepare_value(value):
    if isinstance(value, Enum):
        return value.value
    return value


def dict_factory(trim_trailing_underscore=True, skip_none=False, skip_internal=False):
    """
    Формируем словарь с данными из dataclass со следующими ограничениями:
      1. Пропускаем все элементы, которые назваются с первого символа `_` - это внутренние свойства
      2. отрезаем конечный символ `_`, так как он используется только для исключения конфликта
          с ключевыми словами и встроенными функциями python
      3. Пропускаются None значения
    """

    def impl(data):
        return {
            (k.rstrip("_") if trim_trailing_underscore else k): _prepare_value(v)
            for k, v in data
            if not (k.startswith("_") and skip_internal) and (v is not None or not skip_none)
        }

    return impl
