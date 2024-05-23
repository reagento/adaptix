from dataclasses import dataclass
from typing import Literal, Optional, Union

import pytest
from sqlalchemy import JSON, create_engine, insert, null, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, defer, mapped_column, sessionmaker

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


retort = Retort()


class AuditLogRecord(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[AnyAuditLog] = mapped_column(AdaptixJSON(retort, AnyAuditLog))


@pytest.fixture()
def engine():
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(engine)


@pytest.fixture()
def session(session_factory):
    with session_factory() as session:
        yield session


def test_add(session):
    session.add(
        AuditLogRecord(
            data=UserCreated(
                id=1,
                name="Example",
            ),
        ),
    )
    session.commit()


def test_insert(session):
    session.execute(
        insert(AuditLogRecord)
        .values(
            data=UserChanged(
                id=1,
                name="Example",
            ),
        ),
    )
    session.commit()


def test_select(session):
    session.add(
        AuditLogRecord(
            data=UserCreated(
                id=1,
                name="Example",
            ),
        ),
    )
    session.commit()

    record = session.scalar(
        select(AuditLogRecord)
        .where(AuditLogRecord.data["id"].as_integer() == 1),
    )
    assert record.data == UserCreated(
        id=1,
        name="Example",
    )


def test_update(session):
    session.add(
        AuditLogRecord(
            data=UserCreated(
                id=1,
                name="Example1",
            ),
        ),
    )
    session.add(
        AuditLogRecord(
            data=UserChanged(
                id=1,
                name="Example2",
            ),
        ),
    )
    session.commit()

    session.execute(
        update(AuditLogRecord)
        .where(
            AuditLogRecord.data["id"].as_integer() == 1,
            AuditLogRecord.data["tag"].as_string() == UserChanged.tag,
        )
        .values(
            data=UserChanged(
                id=1,
                name="Example3",
            ),
        ),
    )
    assert session.get(AuditLogRecord, 1).data.name == "Example1"
    assert session.get(AuditLogRecord, 2).data.name == "Example3"


def test_mutation_tracking(session_factory):
    with session_factory() as session:
        session.add(
            AuditLogRecord(
                data=UserCreated(
                    id=1,
                    name="Example",
                ),
            ),
        )
        session.commit()

    with session_factory() as session:
        record = session.get(AuditLogRecord, 1)
        record.data.name = "Example2"
        session.commit()

    with session_factory() as session:
        record = session.get(AuditLogRecord, 1)
        assert record.data.name == "Example"  # (!) mutation tracking does not work (!)


@pytest.mark.parametrize(
    "record_factory",
    [
        pytest.param(lambda: AuditLogRecord(data=None), id="explicit None"),
        pytest.param(lambda: AuditLogRecord(), id="explicit None"),
    ],
)
def test_late_init(session_factory, record_factory):
    with session_factory() as session:
        record = record_factory()
        record.data = UserCreated(
            id=1,
            name="Example",
        )
        session.add(record)
        session.commit()

    with session_factory() as session:
        record = session.get(AuditLogRecord, 1, options=[defer(AuditLogRecord.data)])
        assert record.data == UserCreated(
            id=1,
            name="Example",
        )


class AuditLogRecordNullable(Base):
    __tablename__ = "audit_log_nullable"

    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[Optional[AnyAuditLog]] = mapped_column(AdaptixJSON(retort, AnyAuditLog))


@pytest.mark.parametrize(
    "none_value",
    [
        None,
        null(),
        JSON.NULL,
    ],
)
def test_insert_none(session_factory, none_value):
    with session_factory() as session:
        session.add(
            AuditLogRecordNullable(
                data=none_value,
            ),
        )
        session.commit()

    with session_factory() as session:
        record = session.get(AuditLogRecordNullable, 1)
        assert record.data is None
