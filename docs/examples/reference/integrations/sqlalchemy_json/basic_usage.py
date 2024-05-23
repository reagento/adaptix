# mypy: disable-error-code="union-attr"
from sqlalchemy import insert
from sqlalchemy.orm import Session

from .helpers import run_with_session
from .preamble import AuditLogRecord, UserChanged, UserCreated


def example(session: Session) -> None:
    session.add(
        AuditLogRecord(
            data=UserCreated(id=1, name="Sam"),
        ),
    )

    session.execute(
        insert(AuditLogRecord)
        .values(
            data=UserChanged(id=1, name="Leo"),
        ),
    )
    session.commit()

    assert session.get(AuditLogRecord, 1).data == UserCreated(id=1, name="Sam")
    assert session.get(AuditLogRecord, 2).data == UserChanged(id=1, name="Leo")


run_with_session(example)
