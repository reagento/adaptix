from dataclasses import dataclass
from typing import Literal, Union

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from adaptix import Retort
from adaptix.integrations.sqlalchemy import AdaptixJSON


@dataclass
class UserCreated:
    id: int
    name: str

    tag: Literal["user_created"] = "user_created"


@dataclass
class UserChanged:
    id: int
    name: str

    tag: Literal["user_changed"] = "user_changed"


AnyAuditLog = Union[UserCreated, UserChanged]


class Base(DeclarativeBase):
    pass


db_retort = Retort()


class AuditLogRecord(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[AnyAuditLog] = mapped_column(AdaptixJSON(db_retort, AnyAuditLog))
