from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

from adaptix import Retort, as_sentinel, name_mapping
from adaptix.load_error import AggregateLoadError, TypeLoadError


class MySentinel(Enum):
    VALUE = "VALUE"


@dataclass
class PatchBook:
    id: int
    title: Union[str, MySentinel] = MySentinel.VALUE
    sub_title: Union[Optional[str], MySentinel] = MySentinel.VALUE


retort = Retort(
    recipe=[
        name_mapping(omit_default=True),
        as_sentinel(MySentinel),
    ],
)


data = {"id": 435}
patch_book = retort.load(data, PatchBook)
assert patch_book == PatchBook(
    id=435,
    title=MySentinel.VALUE,
    sub_title=MySentinel.VALUE,
)
assert retort.dump(patch_book) == data

data_with_none = {"id": 435, "sub_title": None}
patch_book = retort.load(data_with_none, PatchBook)
assert patch_book == PatchBook(
    id=435,
    title=MySentinel.VALUE,
    sub_title=None,
)
assert retort.dump(patch_book) == data_with_none

data_with_none = {"id": 435, "title": None}
try:
    patch_book = retort.load(data_with_none, PatchBook)
except AggregateLoadError as e:
    assert len(e.exceptions) == 1
    assert isinstance(e.exceptions[0], TypeLoadError)
    assert e.exceptions[0].expected_type is str
