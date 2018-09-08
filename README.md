# dataclass_factory
## Why

You can convert dataclass to dict using `asdict` method, but cannot convert back.
This module provides `parse` method for such task. 

## What's supported 

* `dataclass` from dict
* `Enum` from value
* `List`, `Tuple`, `Set`, `FrozenSet`, `Dict` with specified type
* `Optional` with specified type
* `Union` parsed in order of given types

## Usage

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
