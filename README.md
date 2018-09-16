# dataclass_factory

[![PyPI version](https://badge.fury.io/py/dataclass-factory.svg)](https://badge.fury.io/py/dataclass-factory)
[![Build Status](https://travis-ci.org/Tishka17/dataclass_factory.svg?branch=master)](https://travis-ci.org/Tishka17/dataclass_factory)

## Why

You can convert dataclass to dict using `asdict` method, but cannot convert back.
This module provides `parse` method for such task. 

## What's supported 

* `dataclass` from dict
* `Enum` from value
* `List`, `Set`, `FrozenSet`, `Dict` with specified type
* `Tuple` with specified types or ellipsis
* `Optional` with specified type
* `Union` parsed in order of given types
* `Any` returned as is

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