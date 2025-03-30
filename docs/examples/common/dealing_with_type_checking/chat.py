# ruff: noqa: UP035, UP006
from dataclasses import dataclass
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .message import Message


@dataclass
class Chat:
    id: int
    name: str
    messages: List["Message"]
