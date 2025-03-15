from dataclasses import dataclass
from pathlib import Path

import pytest

from adaptix import Retort, name_mapping, with_property
from adaptix._internal.model_tools.definitions import DefaultFactory, DefaultFactoryWithSelf, DefaultValue


@dataclass
class SimpleProperty:
    name: str
    price: float

    @property
    def discounted_price(self) -> float:
        return self.price * 0.9


@pytest.mark.parametrize(
    "prop",
    [
        pytest.param("discounted_price", id="string"),
        pytest.param(SimpleProperty.discounted_price, id="property_object"),
    ],
)
def test_simple_property(prop):
    retort = Retort(
        recipe=[
            with_property(SimpleProperty, prop),
        ],
    )

    assert retort.load(
        {
            "name": "Laptop",
            "price": 1000.0,
        },
        SimpleProperty,
    ) == SimpleProperty(name="Laptop", price=1000.0)

    assert (
        retort.dump(SimpleProperty(name="Laptop", price=1000.0))
        ==
        {
            "name": "Laptop",
            "price": 1000.0,
            "discounted_price": 900.0,
        }
    )


@dataclass
class DefinePropType:
    name: str
    price: float

    @property
    def some_path(self):
        return Path("/") / self.name


@pytest.mark.parametrize(
    "prop",
    [
        pytest.param("some_path", id="string"),
        pytest.param(DefinePropType.some_path, id="property_object"),
    ],
)
def test_define_type_property(prop):
    retort = Retort(
        recipe=[
            with_property(DefinePropType, prop, Path),
        ],
    )

    assert (
        retort.dump(DefinePropType(name="Laptop", price=1000.0))
        ==
        {
            "name": "Laptop",
            "price": 1000.0,
            "some_path": "/Laptop",
        }
    )


@dataclass
class OverridePropType:
    name: str
    price: float

    @property
    def some_path(self) -> float:
        return Path("/") / self.name


@pytest.mark.parametrize(
    "prop",
    [
        pytest.param("some_path", id="string"),
        pytest.param(OverridePropType.some_path, id="property_object"),
    ],
)
def test_override_type_property(prop):
    retort = Retort(
        recipe=[
            with_property(OverridePropType, prop, Path),
        ],
    )

    assert (
        retort.dump(OverridePropType(name="Laptop", price=1000.0))
        ==
        {
            "name": "Laptop",
            "price": 1000.0,
            "some_path": "/Laptop",
        }
    )


@dataclass
class PropWithDefault:
    name: str
    price: float = 0.0

    @property
    def discounted_price(self) -> float:
        return self.price * 0.9


@pytest.mark.parametrize(
    "prop",
    [
        pytest.param("discounted_price", id="string"),
        pytest.param(PropWithDefault.discounted_price, id="property_object"),
    ],
)
@pytest.mark.parametrize(
    "default",
    [
        pytest.param(DefaultValue(0), id="default_value"),
        pytest.param(DefaultFactory(lambda: 0), id="default_factory"),
        pytest.param(DefaultFactoryWithSelf(lambda self: 0), id="default_factory_with_self"),
    ],
)
def test_default(prop, default):
    retort = Retort(
        recipe=[
            with_property(PropWithDefault, prop, default=default),
            name_mapping(omit_default=True),
        ],
    )

    assert (
        retort.dump(PropWithDefault(name="Laptop", price=1000.0))
        ==
        {
            "name": "Laptop",
            "price": 1000.0,
            "discounted_price": 900.0,
        }
    )
    assert (
        retort.dump(PropWithDefault(name="Laptop", price=0))
        ==
        {
            "name": "Laptop",
        }
    )


@dataclass
class PropWithAccessError:
    name: str
    price: float

    @property
    def discounted_price(self) -> float:
        if self.price == 0:
            raise ValueError
        return self.price * 0.9


@pytest.mark.parametrize(
    "prop",
    [
        pytest.param("discounted_price", id="string"),
        pytest.param(PropWithAccessError.discounted_price, id="property_object"),
    ],
)
def test_access_error(prop):
    retort = Retort(
        recipe=[
            with_property(PropWithAccessError, prop, access_error=ValueError),
            name_mapping(omit_default=True),
        ],
    )

    assert (
        retort.dump(PropWithAccessError(name="Laptop", price=1000.0))
        ==
        {
            "name": "Laptop",
            "price": 1000.0,
            "discounted_price": 900.0,
        }
    )
    assert (
        retort.dump(PropWithAccessError(name="Laptop", price=0))
        ==
        {
            "name": "Laptop",
            "price": 0,
        }
    )
