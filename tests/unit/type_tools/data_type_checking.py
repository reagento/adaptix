import typing
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    IntSeq = Sequence[int]


if typing.TYPE_CHECKING:
    StrSeq = Sequence[str]


class Foo:
    a: bool
    b: "IntSeq"
    c: "StrSeq"
