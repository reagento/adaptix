# dataclass_factory

[![PyPI version](https://badge.fury.io/py/dataclass-factory.svg)](https://badge.fury.io/py/dataclass-factory)
[![Build Status](https://travis-ci.org/Tishka17/dataclass_factory.svg?branch=master)](https://travis-ci.org/Tishka17/dataclass_factory)

**dataclass_factory** is modern way to convert dataclasses or other objects to and from more common types like dicts

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
* Enums, typed dicts and lists are supported from the box

## Usage

### Parsers and serializers

To parse dict create factory, get and use `parser`  or just call `load` method 

```python
factory = dataclass_factory.Factory()
parser = factory.parser(Book)  # save it to reuse multiple times
book = parser(data)
# or 
book = factory.load(data, Book) 
```

**Important**:
When parsing data of `Union` type parsing stops when no ValueError/TypeError detected. 
So the order of type arguments is important.


Serialization is also very simple:
```python
factory = dataclass_factory.Factory()
serializer = factory.serializer(Book)  # save it to reuse multiple times
data = serializer(book)
# or 
data = factory.dump(book, Book) 
```

If no class is provided in `dump` method it will find serializer based on real type of object.

Every parser/serializer is created when it is used (or retrieved from factory) for first time. 
Factory caches all created parsers and serializers so create it only once for every settings bundle. 

**Important**:
When serializing data of `Union` type, type arguments are ignored and serializer is detected based on real data type.

### Configuring

```python
Factory(debug_path: bool, default_schema: Schema, schemas: Dict[Type, Schema])
```

#### More verbose errors

`debug_path` parameter of Factory is used to enable verbose error mode. 

It this mode `InvalidFieldError` is thrown when some dataclass field cannot be parsed. 
It contains `field_path` which is path to the field in provided data (key and indexes).

#### Schemas

`Schema` instances used to change behavior of parsing/serializing certain classes or in general.  

* `default_schema` is `Schema` which is used by default.
* `schemas` is dict, with types as keys, and corresponding `Schema` instances as values. 

If some setting is not set for schema (or set to `None`), setting from `default_schema` is used. 
If it is also not set, library default will be used

Schema consists of:
* 