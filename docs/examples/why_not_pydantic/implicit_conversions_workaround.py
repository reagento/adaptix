# mypy: disable-error-code="arg-type"
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, ValidationError


class Product(BaseModel):
    id: int
    amount: Decimal

    model_config = ConfigDict(strict=True)


try:
    Product(id=1, amount=14.6)
except ValidationError:
    pass

assert (
    Product.model_validate({"id": 1, "amount": 14.6}, strict=False)
    ==
    Product(id=1, amount=Decimal("14.6"))
)
