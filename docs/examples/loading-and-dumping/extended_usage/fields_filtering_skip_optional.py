# mypy: disable-error-code="arg-type"
from dataclasses import dataclass

from adaptix import Retort, name_mapping


@dataclass
class User:
    id: int
    name: str
    trust_rating: float = 0


retort = Retort(
    recipe=[
        name_mapping(
            User,
            skip=['trust_rating'],
        ),
    ]
)


data = {
    'id': 52,
    'name': 'Ken Thompson',
}
data_with_trust_rating = {
    **data,
    'trust_rating': 100,
}
assert retort.load(data, User) == User(id=52, name='Ken Thompson')
assert retort.load(data_with_trust_rating, User) == User(id=52, name='Ken Thompson')
assert retort.dump(User(id=52, name='Ken Thompson', trust_rating=100)) == data
