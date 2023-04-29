from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from adaptix import Retort

from .adapter import ModelJSON
from .audit_logs import AnyAuditLog


class Base(DeclarativeBase):
    pass


RETORT = Retort()


class AuditLogRecord(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[AnyAuditLog] = mapped_column(ModelJSON(AnyAuditLog, RETORT))

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
