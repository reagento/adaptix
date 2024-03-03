import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from adaptix import P, Retort, name_mapping


@dataclass
class Document:
    key: str

    redirects: List[str]
    edition_keys: List[str]
    lcc_list: List[str]


def create_plural_stripper(
    *,
    exclude: Sequence[str] = (),
    suffixes: Iterable[str] = ("s", "_list"),
):
    pattern = "^(.*)(" + "|".join(suffixes) + ")$"

    def plural_stripper(shape, fld):
        return re.sub(pattern, lambda m: m[1], fld.id)

    return (
        P[pattern] & ~P[tuple(exclude)],
        plural_stripper,
    )


retort = Retort(
    recipe=[
        name_mapping(
            Document,
            map=[
                {"key": "name"},
                create_plural_stripper(exclude=["redirects"]),
            ],
        ),
    ],
)
data = {
    "name": "The Lord of the Rings",
    "redirects": ["1234"],
    "edition_key": ["423", "4235"],
    "lcc": ["675", "345"],
}
document = retort.load(data, Document)
assert document == Document(
    key="The Lord of the Rings",
    redirects=["1234"],
    edition_keys=["423", "4235"],
    lcc_list=["675", "345"],
)
assert retort.dump(document) == data
