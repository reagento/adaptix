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


@pytest.fixture
def session(session_factory):
    with session_factory() as session:
        yield session


def test_add(session):
    session.add(
        AuditLogRecord(
            data=UserCreated(
                id=1,
                name='Example',
            ),
        )
    )
    session.commit()


def test_insert(session):
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


def test_select(session):
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


def test_update(session):
    # audit logs are not supposed to be updated...
    user_created_record = AuditLogRecord(
        data=UserCreated(
            id=1,
            name='Example1',
        ),
    )
    user_changed_record = AuditLogRecord(
        data=UserChanged(
            id=1,
            name='Example2',
        ),
    )
    session.add(user_created_record)
    session.add(user_changed_record)
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

    session.refresh(user_created_record)
    session.refresh(user_changed_record)
    assert user_created_record.data.name == 'Example1'
    assert user_changed_record.data.name == 'Example3'


def test_mutation_tracking(session_factory):
    """SQLAlchemy flushes object only if there are some that are marked as modified (dirty).
    The instance becomes dirty when ``__setattr__`` is invoked.
    So, SQLAlchemy can not track the mutation of object associated with attribute.

    There are 3 workarounds to solve this problem:
    1) Modify the entire object graph to track mutation at any edge.
       See for details https://docs.sqlalchemy.org/en/20/orm/extensions/mutable.html
    2) Save a copy of the dataclass at the 'after_attach' event
       and compares it with an actual object at 'before_flush'.
       If it differs, mark the instance as dirty via `flag_modified`.
       This will work only if `session.flush()` is called directly.
       Other methods may skip calling flush (and invoking its events) if there are no dirty objects.
    3) Call `flag_modified` directly after dataclass mutation.

    Finally, it is not recommended to mutate a model that will be persistent to JSON,
    because more likely it means that you should not store JSON in RDBMS.
    """

    with session_factory() as session:
        record = AuditLogRecord(
            data=UserCreated(
                id=1,
                name='Example',
            ),
        )
        session.add(record)
        session.flush()

        record_id = record.id
        session.commit()

    with session_factory() as session:
        record = session.get(AuditLogRecord, record_id)
        record.data.name = 'Example2'
        session.commit()

    with session_factory() as session:
        record = session.get(AuditLogRecord, record_id)
        assert record.data.name == 'Example'  # (!) mutation tracking does not work (!)
