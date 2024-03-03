from dataclasses import dataclass

from adaptix import Retort, constructor, loader, name_mapping


@dataclass
class Device:
    name: str
    x: float
    y: float

    @classmethod
    def from_config(cls, name: str, coordinates: str):
        x, y = coordinates.split()
        return Device(name, float(x), float(y))


def test_simple():
    retort = Retort(
        recipe=[
            constructor(Device, Device.from_config),
        ],
    )
    assert (
        retort.load({"name": "dxf", "coordinates": "1 2"}, Device)
        ==
        Device(name="dxf", x=1, y=2)
    )


def test_name_mapping():
    retort = Retort(
        recipe=[
            constructor(Device, Device.from_config),
            name_mapping(
                Device,
                map={"coordinates": "coords"},
            ),
        ],
    )
    assert (
        retort.load({"name": "dxf", "coords": "1 2"}, Device)
        ==
        Device(name="dxf", x=1, y=2)
    )


def device_loader(data):
    raise RuntimeError


def test_override_loader():
    retort = Retort(
        recipe=[
            constructor(Device, Device.from_config),
            loader(Device, device_loader),
        ],
    )
    assert (
        retort.load({"name": "dxf", "coordinates": "1 2"}, Device)
        ==
        Device(name="dxf", x=1, y=2)
    )


def test_self():
    retort = Retort(
        recipe=[
            constructor(Device, Device),
        ],
    )
    assert (
        retort.load({"name": "dxf", "x": 1, "y": 2}, Device)
        ==
        Device(name="dxf", x=1, y=2)
    )
