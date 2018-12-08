# dataclass_factory

[![PyPI version](https://badge.fury.io/py/dataclass-factory.svg)](https://badge.fury.io/py/dataclass-factory)
[![Build Status](https://travis-ci.org/Tishka17/dataclass_factory.svg?branch=master)](https://travis-ci.org/Tishka17/dataclass_factory)

## Dataclass instance creation library

You can convert dataclass to dict using `asdict` method, but cannot convert back.
This module provides `ParserFactory` method for such task. 

It is very useful in combination with json

## What's supported 

* `dataclass` from dict
* `Enum` from its value
* `List`, `Set`, `FrozenSet`, `Dict`
* `Tuple` with specified types or ellipsis
* `Optional` with specified type
* `Union` parsed in order of given types
* `Any` returned as is
* `int`/`float`/`decimal` also parsed from string
* other classes based on their `__init__` method
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

parserFactory = dataclass_factory.ParserFactory()
obj = parserFactory.get_parser(Book)(data)  # Same as Book(title="Fahrenheit 451")

```

You need to create parserFactory only once at the startup of your app.
It caches created parsers and it will be significantly quicker than creating parser each time.

### Extended usage

Parser factory provides some useful options:

* `trim_trailing_underscore` (enabled by default) - allows to trim trailing unders score in dataclass field names when looking them in corresponding dictionary.  
    For example field `id_` can be stored is `id`
* `debug_path` - allows to see path to an elemetn, that cannot be parsed in raised Exception.  
    This causes some permfomance decrease
* `type_factories` - dictionary with type as a key and functions that can be used to create intances of corresponding types as value.  
    See [below](#custom-parsers-and-dict-factory).

### Custom parsers and dict factory

You can provide your parsers for types that are not supported. For example, you can parse `datetime` from iso format.

Also there is `dict_factory`, which can help you to serialize data in your dataclasses. 
You can provide custom serializers as well


```python
from dataclass_factory import ParserFactory, dict_factory
from datetime import datetime
import dateutil.parser
from dataclasses import dataclass, asdict


parserFactory = ParserFactory(type_factories={datetime: dateutil.parser.parse})


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
assert todo == parserFactory.get_parser(Todo)(data)

assert data == asdict(
    todo,
    dict_factory=dict_factory(
        trim_trailing_underscore=True,
        type_serializers={datetime: datetime.isoformat}
    )
)
```

### Compatibility

In versions below 1.0 there was a simple `parse` method. 

It is still provided for compatibility, but is not recommended because it recreates ParserFactory each time it is called
It can be removed in some future version
