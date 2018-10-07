# dataclass_factory

[![PyPI version](https://badge.fury.io/py/dataclass-factory.svg)](https://badge.fury.io/py/dataclass-factory)
[![Build Status](https://travis-ci.org/Tishka17/dataclass_factory.svg?branch=master)](https://travis-ci.org/Tishka17/dataclass_factory)

## Why

You can convert dataclass to dict using `asdict` method, but cannot convert back.
This module provides `parse` method for such task. 

It is very useful in combination with json

## What's supported 

* `dataclass` from dict
* `Enum` from value
* `List`, `Set`, `FrozenSet`, `Dict` with specified type
* `Tuple` with specified types or ellipsis
* `Optional` with specified type
* `Union` parsed in order of given types
* `Any` returned as is
* other classes based on their `__init__` method
* `int`/`float`/`decimal` also parsed from string
* custom parser if specified

## Usage

Install:
```bash
pip install dataclass_factory 
```

Code:

```python
@dataclass
class Book:
    title: str
    author: str = "Unknown author"


data = {
    "title": "Fahrenheit 451"
}

obj = dataclass_factory.parse(data, Book)  # Same as Book(title="Fahrenheit 451")

```


### More complex example

```python
@dataclass 
class Disk:
    title: str
    artist: str
    
    
@dataclass
class Store:
    items: List[Union[Disk, Book]]
     


data = {
    "items": [
        {"title": "Fahrenheit 451", "author": "Bradbury"},
        {"title": "Dark Side of the Moon", "artist": "Pink Floyd"}
    ]
}

expected = Store(
    items=[
        Book(title='Fahrenheit 451', author='Bradbury'),
        Disk(title='Dark Side of the Moon', artist='Pink Floyd')
    ]
)

assert expected == dataclass_factory.parse(data, Store)

```

### Custom parsers and dict factory

You can provide your parsers for types that are not supported. For example, you can parse `datetime` from iso format.

Also there is `dict_factory`, which can help you to serialize data in your dataclasses. 
You can provide custom serializers as well


```python
from dataclass_factory import parse, dict_factory
from datetime import datetime
import dateutil.parser
from dataclasses import dataclass, asdict


@dataclass
class Todo:
    id_: int
    title: str
    deadline: datetime


data = {
    "id": 1,
    "deadline": "2025-12-31T00:00:00",
    "title": "Release 1.0"
}

todo = Todo(
    id_=1,
    title="Release 1.0",
    deadline=datetime(2025, 12, 31, 0, 0, 0)
)

assert todo == parse(
    data,
    Todo,
    trim_trailing_underscore=True,
    type_factories={datetime: dateutil.parser.parse}
)

assert data == asdict(
    todo,
    dict_factory=dict_factory(
        trim_trailing_underscore=True,
        type_serializers={datetime: datetime.isoformat}
    )
)
```