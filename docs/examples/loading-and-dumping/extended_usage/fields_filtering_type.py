# mypy: disable-error-code="arg-type"
from dataclasses import dataclass

from adaptix import Retort, dumper, loader, name_mapping


class HiddenStr(str):
    def __repr__(self):
        return "'<hidden>'"


@dataclass
class User:
    id: int
    name: str
    password_hash: HiddenStr


retort = Retort(
    recipe=[
        loader(HiddenStr, HiddenStr),
        dumper(HiddenStr, str),
    ]
)
skipping_retort = retort.extend(
    recipe=[
        name_mapping(
            User,
            skip=HiddenStr,
        ),
    ]
)

user = User(
    id=52,
    name='Ken Thompson',
    password_hash=HiddenStr('ZghOT0eRm4U9s'),
)
data = {
    'id': 52,
    'name': 'Ken Thompson',
}
data_with_password_hash = {
    **data,
    'password_hash': 'ZghOT0eRm4U9s',
}
assert repr(user) == "User(id=52, name='Ken Thompson', password_hash='<hidden>')"
assert retort.dump(user) == data_with_password_hash
assert retort.load(data_with_password_hash, User) == user
assert skipping_retort.dump(user) == data
