# mypy: disable-error-code="union-attr"
from sqlalchemy import select
from sqlalchemy.orm import Session

from .helpers import run_with_session
from .preamble import AuditLogRecord, UserCreated


def example(session: Session) -> None:
    session.add(
        AuditLogRecord(
            data=UserCreated(
                id=1,
                name="Sam",
            ),
        ),
    )
    session.commit()

    record = session.scalar(
        select(AuditLogRecord)
        .where(AuditLogRecord.data["id"].as_integer() == 1),
    )
    assert record.data == UserCreated(id=1, name="Sam")


run_with_session(example)
