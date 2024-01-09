<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo/adaptix-with-title-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/logo/adaptix-with-title-light.png">
    <img alt="adaptix logo" src="docs/logo/adaptix-with-title-light.png">
  </picture>

  <hr>

  [![PyPI version](https://img.shields.io/pypi/v/adaptix.svg?color=blue)](https://pypi.org/project/adaptix/)
  [![downloads](https://img.shields.io/pypi/dm/adaptix.svg)](https://pypistats.org/packages/adaptix)
  [![versions](https://img.shields.io/pypi/pyversions/adaptix.svg)](https://github.com/reagento/adaptix)
  [![license](https://img.shields.io/github/license/reagento/dataclass_factory.svg)](https://github.com/reagento/adaptix/blob/master/LICENSE)
</div>

An extremely flexible and configurable data model conversion library.

> [!IMPORTANT]
> Adaptix is ready for production!
> The beta version only means there may be some backward incompatible changes, so you need to pin a specific version.

📚 [Documentation](https://adaptix.readthedocs.io/)

## TL;DR

Install
```bash
pip install adaptix==3.0.0b1
```

Use
```python
from dataclasses import dataclass

from adaptix import Retort


@dataclass
class Book:
    title: str
    price: int
    author: str = "Unknown author"


data = {
    "title": "Fahrenheit 451",
    "price": 100,
}

# Retort is meant to be global constant or just one-time created
retort = Retort()

book = retort.load(data, Book)
assert book == Book(title="Fahrenheit 451", price=100)
assert retort.dump(book) == data
```

## Use cases

* Validation and transformation of received data for your API.
* Config loading/dumping via codec that produces/takes dict.
* Storing JSON in a database and representing it as a model inside the application code.
* Creating API clients that convert a model to JSON sending to the server.
* Persisting entities in cache storage.
* Implementing fast and primitive ORM.

## Advantages

* Sane defaults for JSON processing, no configuration is needed for simple cases.
* Separated model definition and rules of conversion
  that allow preserving [SRP](https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html)
  and have different representations for one model.
* Speed. It is one of the fastest data parsing and serialization libraries.
* There is no forced model representation, adaptix can adjust to your needs.
* Support [dozens](https://adaptix.readthedocs.io/en/latest/loading-and-dumping/specific-types-behavior.html) of types,
  including different model kinds:
  ``@dataclass``, ``TypedDict``, ``NamedTuple``, and [``attrs``](https://www.attrs.org/en/stable/)
* Working with self-referenced data types (such as linked lists or trees).
* Saving [path](https://adaptix.readthedocs.io/en/latest/loading-and-dumping/tutorial.html#error-handling)
  where an exception is raised (including unexpected errors).
* Machine-readable [errors](https://adaptix.readthedocs.io/en/latest/loading-and-dumping/tutorial.html#error-handling)
  that could be dumped.
* Support for user-defined generic models.
* Automatic name style conversion (e.g. `snake_case` to `camelCase`).
* [Predicate system](https://adaptix.readthedocs.io/en/latest/loading-and-dumping/tutorial.html#predicate-system)
  that allows to concisely and precisely override some behavior.
* Disabling additional checks to speed up data loading from trusted sources.
* No auto casting by default. The loader does not try to guess value from plenty of input formats.
