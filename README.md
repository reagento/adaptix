# dataclass_factory

[![PyPI version](https://badge.fury.io/py/dataclass-factory.svg)](https://badge.fury.io/py/dataclass-factory)
[![Build Status](https://travis-ci.org/Tishka17/dataclass_factory.svg?branch=master)](https://travis-ci.org/Tishka17/dataclass_factory)
[![downloads](https://img.shields.io/pypi/dm/dataclass_factory.svg)](https://pypistats.org/packages/dataclass_factory)
[![license](https://img.shields.io/github/license/Tishka17/dataclass_factory.svg)](https://github.com/Tishka17/dataclass_factory/blob/master/LICENSE)

**dataclass_factory** is a modern way to convert dataclasses or other objects to and from more common types like dicts

> [!IMPORTANT]
> The new major version is [out](https://adaptix.readthedocs.io/en/latest/)
> The library was renamed to *adaptix* due to extending of the working scope.
>
> This update features:
> 1. Support for model-to-model conversion.
> 2. Support for attrs and sqlalchemy (integration with many other libraries is coming).
> 3. Fully redesigned API helping to follow DRY.
> 4. Performance improvements of [up to two times](https://adaptix.readthedocs.io/en/latest/benchmarks.html)


## Help

See [documentation](https://dataclass-factory.readthedocs.io/) for more details.

## TL;DR

Install
```bash
pip install dataclass_factory
```

Use
```python
from dataclasses import dataclass
import dataclass_factory


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


data = {
    "title": "Fahrenheit 451",
    "price": 100,
}

factory = dataclass_factory.Factory()
book: Book = factory.load(data, Book)  # Same as Book(title="Fahrenheit 451", price=100)
serialized = factory.dump(book)
```

## Requirements

* python >= 3.6

You can use `dataclass_factory` with python 3.6 and `dataclass` library installed from pip.

On python 3.7 it has no external dependencies outside of the Python standard library.

## Advantages

* No schemas or configuration needed for simple cases. Just create `Factory` and call `load`/`dump` methods
* Speed. It is up to 10 times faster than `marshmallow` and `dataclasses.asdict` (see [benchmarks](benchmarks))
* Automatic name style conversion (e.g. `snake_case` to `CamelCase`)
* Automatic skipping of "internal use" fields (with leading underscore)
* Enums, typed dicts, tuples and lists are supported out of the box
* Unions and Optionals are supported without need to define them in schema
* Generic dataclasses can be automatically parsed as well
* Cyclic-referenced structures (such as linked-lists or trees) also can be converted
* Validators, custom parser steps are supported.
* Multiple schemas for single type can be provided to support different ways of parsing of the same type
