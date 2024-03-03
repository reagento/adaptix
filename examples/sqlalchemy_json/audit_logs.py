from dataclasses import dataclass
from typing import Literal, Union


@dataclass
class AuditLog:
    pass


@dataclass
class UserCreated(AuditLog):
    id: int
    name: str

    tag: Literal["user_created"] = "user_created"


@dataclass
class UserChanged(AuditLog):
    id: int
    name: str

    tag: Literal["user_changed"] = "user_changed"


@dataclass
class UserDeleted(AuditLog):
    id: int

    tag: Literal["user_deleted"] = "user_deleted"


AnyAuditLog = Union[
    UserCreated,
    UserChanged,
    UserDeleted,
]
