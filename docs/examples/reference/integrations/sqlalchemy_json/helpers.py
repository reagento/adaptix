from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .preamble import Base

SessionFactory = Callable[[], Session]


@contextmanager
def create_prepared_engine() -> Iterator[Engine]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@contextmanager
def create_session_factory() -> Iterator[SessionFactory]:
    with create_prepared_engine() as engine:
        yield sessionmaker(engine)


def run_with_session(func: Callable[[Session], Any]):
    with create_session_factory() as session_factory, session_factory() as session:
        func(session)


def run_with_session_factory(func: Callable[[SessionFactory], Any]):
    with create_session_factory() as session_factory:
        func(session_factory)
