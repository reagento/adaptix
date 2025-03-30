from dataclasses import dataclass
from typing import Optional, Union

from adaptix import P, Retort, as_sentinel, name_mapping
from adaptix.load_error import AggregateLoadError, TypeLoadError


@dataclass
class PatchBook:
    id: int
    title: Optional[str] = None
    sub_title: Optional[str] = None


retort = Retort(
    recipe=[
        name_mapping(omit_default=True),
        as_sentinel(P[PatchBook][Union][None]),
    ],
)


data = {"id": 435}
patch_book = retort.load(data, PatchBook)
assert patch_book == PatchBook(
    id=435,
    title=None,
    sub_title=None,
)
assert retort.dump(patch_book) == data

data_with_none = {"id": 435, "sub_title": None}
try:
    patch_book = retort.load(data_with_none, PatchBook)
except AggregateLoadError as e:
    assert len(e.exceptions) == 1
    assert isinstance(e.exceptions[0], TypeLoadError)
    assert e.exceptions[0].expected_type is str
