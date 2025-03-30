from typing import NotRequired, TypedDict

from adaptix import Retort


class PatchBook(TypedDict):
    id: int
    title: NotRequired[str]
    sub_title: NotRequired[str]


retort = Retort()

data = {"id": 435}
patch_book = retort.load(data, PatchBook)
assert patch_book == PatchBook(id=435)
assert retort.dump(patch_book, PatchBook) == data
