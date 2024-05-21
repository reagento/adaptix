from sqlalchemy.orm import Mapped, mapped_column

from adaptix._internal.integrations.sqlalchemy.orm import AdaptixJSON

from .preamble import AnyAuditLog, Base, db_retort


def example() -> None:
    from sqlalchemy import JSON

    class AuditLogRecord(Base):
        __tablename__ = "audit_logs2"

        id: Mapped[int] = mapped_column(primary_key=True)
        data: Mapped[AnyAuditLog] = mapped_column(
            AdaptixJSON(db_retort, AnyAuditLog, impl=JSON(none_as_null=True)),
        )


example()
