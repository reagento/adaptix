from dataclasses import asdict, dataclass

from adaptix import P, with_property
from adaptix.conversion import get_converter

from .forward_ref.product import Product
from .forward_ref.tag import Tag


@dataclass
class TagView:
    id: int
    name: str


@dataclass
class ProductView:
    id: int
    name: str
    tags: list[TagView]


def test_cyclic_forward_ref():
    product = Product(
        id=1,
        name="prod_name",
        tags=[Tag(id=1, name="tag1"), Tag(id=2, name="tag2")],
    )
    converter = get_converter(
        Product,
        ProductView,
        recipe=[
            with_property(P[ProductView]["tags"], "tags"),
        ],
    )
    result = converter(product)
    assert asdict(result) == {
        "id": 1,
        "name": "prod_name",
        "tags": [{"id": 1, "name": "tag1"}, {"id": 2, "name": "tag2"}],
    }
