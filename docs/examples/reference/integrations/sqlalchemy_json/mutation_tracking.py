# mypy: disable-error-code="union-attr, assignment"
from .helpers import SessionFactory, run_with_session_factory
from .preamble import AuditLogRecord, UserCreated


def example(session_factory: SessionFactory) -> None:
    with session_factory() as session:
        record = AuditLogRecord(
            data=UserCreated(
                id=1,
                name="Example",
            ),
        )
        session.add(record)
        session.commit()

    with session_factory() as session:
        record = session.get(AuditLogRecord, 1)
        record.data.name = "Example2"
        session.commit()

    with session_factory() as session:
        record = session.get(AuditLogRecord, 1)
        assert record.data.name == "Example"  # (!) mutation tracking does not work (!)


run_with_session_factory(example)
