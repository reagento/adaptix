# pylint: disable=redefined-outer-name
import pytest
from sqlalchemy import insert, select, update
from sqlalchemy.orm import sessionmaker

from tests_helpers import create_sa_engine

from .audit_logs import UserChanged, UserCreated
from .db_models import AuditLogRecord, Base


@pytest.fixture
def engine():
    engine = create_sa_engine()
    try:
        Base.metadata.create_all(engine)
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(engine)


def test_add(session_factory):
    with session_factory() as session:
        session.add(
            AuditLogRecord(
                data=UserCreated(
                    id=1,
                    name='Example',
                ),
            )
        )
        session.commit()


def test_insert(session_factory):
    with session_factory() as session:
        session.execute(
            insert(AuditLogRecord)
            .values(
                data=UserChanged(
                    id=1,
                    name='Example',
                ),
            )
        )
        session.commit()


def test_select(session_factory):
    with session_factory() as session:
        session.add(
            AuditLogRecord(
                data=UserCreated(
                    id=1,
                    name='Example',
                ),
            )
        )
        session.commit()

        # All queries use json representation of model.
        # If there are name_mapping, you should refer to dumped fields
        record = session.scalar(
            select(AuditLogRecord)
            .where(AuditLogRecord.data['id'].as_integer() == 1)
        )
        assert record.data == UserCreated(
            id=1,
            name='Example',
        )


def test_update(session_factory):
    # audit logs are not supposed to be updated...
    with session_factory() as session:
        session.add_all(
            [
                AuditLogRecord(
                    data=UserCreated(
                        id=1,
                        name='Example1',
                    ),
                ),
                AuditLogRecord(
                    data=UserChanged(
                        id=1,
                        name='Example2',
                    ),
                ),
            ]
        )
        session.commit()

        session.execute(
            update(AuditLogRecord)
            .where(
                AuditLogRecord.data['id'].as_integer() == 1,
                AuditLogRecord.data['tag'].as_string() == UserChanged.tag,
            )
            .values(
                data=UserChanged(
                    id=1,
                    name='Example3',
                ),
            )
        )
