from dataclasses import dataclass

from adaptix import NoSuitableProvider, Retort, name_mapping


@dataclass
class User:
    id: int
    name: str
    password_hash: str


retort = Retort(
    recipe=[
        name_mapping(
            User,
            skip=['password_hash'],
        ),
    ]
)


user = User(
    id=52,
    name='Ken Thompson',
    password_hash='ZghOT0eRm4U9s',
)
data = {
    'id': 52,
    'name': 'Ken Thompson',
}
assert retort.dump(user) == data

try:
    retort.get_loader(User)
except NoSuitableProvider:
    pass
