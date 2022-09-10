from create_model import BaseFactory
from models import Receipt
from dataclass_factory_30.facade.provider import NameMapper
from dataclass_factory_30.provider.model import ExtraSkip
from decimal import Decimal


INNER_RECEIPT_FACTORY = BaseFactory(
    recipe=[
        NameMapper(omit_default=False),
    ],
    extra_policy=ExtraSkip(),
)


receipt_parser = INNER_RECEIPT_FACTORY.parser(Receipt)
receipt_serializer = INNER_RECEIPT_FACTORY.serializer(Receipt)

data = {
        "type": "INCOME",
        "items": [
            {
                "name": "Matchbox",
                "price": Decimal("10.0"),
                "quantity": Decimal("3.0"),
            }
        ],
        "taxation": 4,
        "notify": [
            {"type": "email", "value": "mail@example.com"}
        ],
        "version": 1,
    }

parsed_data = receipt_parser(data)
print(parsed_data)
serialized_data = receipt_serializer(parsed_data)
print(serialized_data)
