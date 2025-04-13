from dataclasses import dataclass
from typing import Optional

from adaptix import Omittable, Omitted, Retort, name_mapping
from adaptix.load_error import AggregateLoadError, TypeLoadError


@dataclass
class PatchBook:
    id: int
    title: Omittable[str] = Omitted()
    sub_title: Omittable[Optional[str]] = Omitted()


retort = Retort(
    recipe=[
        name_mapping(omit_default=True),
    ],
)

data = {"id": 435}
patch_book = retort.load(data, PatchBook)
assert patch_book == PatchBook(
    id=435,
    title=Omitted(),
    sub_title=Omitted(),
)
assert retort.dump(patch_book) == data

data_with_none = {"id": 435, "sub_title": None}
patch_book = retort.load(data_with_none, PatchBook)
assert patch_book == PatchBook(
    id=435,
    title=Omitted(),
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
