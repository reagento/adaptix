# mypy: disable-error-code="arg-type"
from decimal import Decimal

from pydantic import BaseModel


class Product(BaseModel):
    id: int
    amount: Decimal


assert Product(id=1, amount=14.6) == Product(id=1, amount=Decimal("14.6"))
