from typing import List, Optional

import pytest
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship
from tests_helpers import sqlalchemy_equals

from adaptix import Retort


def test_simple(accum):
    mapper_registry = registry()

    @mapper_registry.mapped
    class Book:
        __tablename__ = "books"

        id: Mapped[int] = mapped_column(primary_key=True)
        title: Mapped[str]
        price: Mapped[int]

        __eq__ = sqlalchemy_equals

    retort = Retort(recipe=[accum])

    loader = retort.get_loader(Book)
    assert loader({"id": 1, "title": "abc", "price": 100}) == Book(id=1, title="abc", price=100)

    dumper = retort.get_dumper(Book)
    assert dumper(Book(id=1, title="abc", price=100)) == {"id": 1, "title": "abc", "price": 100}


def test_o2o_relationship(accum):
    mapper_registry = registry()

    @mapper_registry.mapped
    class Declarative1:
        __tablename__ = "DeclarativeModel1"

        id: Mapped[int] = mapped_column(primary_key=True)

        __eq__ = sqlalchemy_equals

    @mapper_registry.mapped
    class Declarative2:
        __tablename__ = "DeclarativeModel2"

        id: Mapped[int] = mapped_column(primary_key=True)
        text: Mapped[str]

        parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Declarative1.id))
        parent: Mapped[Optional[Declarative1]] = relationship()

        __eq__ = sqlalchemy_equals

    retort = Retort(recipe=[accum])

    loader = retort.get_loader(Declarative2)
    assert (
        loader({"id": 1, "text": "abc", "parent_id": 100})
        ==
        Declarative2(id=1, text="abc", parent_id=100)
    )
    assert (
        loader({"id": 1, "text": "abc", "parent": {"id": 100}})
        ==
        Declarative2(id=1, text="abc", parent=Declarative1(id=100))
    )
    assert (
        loader({"id": 1, "text": "abc", "parent_id": 100, "parent": {"id": 100}})
        ==
        Declarative2(id=1, text="abc", parent_id=100, parent=Declarative1(id=100))
    )

    dumper = retort.get_dumper(Declarative2)
    assert (
        dumper(Declarative2(id=1, text="abc", parent_id=100))
        ==
        {"id": 1, "text": "abc", "parent_id": 100, "parent": None}
    )
    assert (
        dumper(Declarative2(id=1, text="abc", parent=Declarative1(id=100)))
        ==
        {"id": 1, "text": "abc", "parent_id": None, "parent": {"id": 100}}
    )
    assert (
        dumper(Declarative2(id=1, text="abc", parent_id=100, parent=Declarative1(id=100)))
        ==
        {"id": 1, "text": "abc", "parent_id": 100, "parent": {"id": 100}}
    )


@pytest.mark.parametrize(
    "list_tp",
    [
        List,
        list,
    ],
)
def test_o2m_relationship(accum, list_tp):
    mapper_registry = registry()

    @mapper_registry.mapped
    class Declarative1:
        __tablename__ = "DeclarativeModel1"

        id: Mapped[int] = mapped_column(primary_key=True)
        parent_id: Mapped[int] = mapped_column(ForeignKey("DeclarativeModel2.id"))

        __eq__ = sqlalchemy_equals

    @mapper_registry.mapped
    class Declarative2:
        __tablename__ = "DeclarativeModel2"

        id: Mapped[int] = mapped_column(primary_key=True)
        text: Mapped[str]

        children: Mapped[list_tp[Declarative1]] = relationship()

        __eq__ = sqlalchemy_equals

    retort = Retort(recipe=[accum])

    loader = retort.get_loader(Declarative2)
    assert (
        loader({"id": 1, "text": "abc", "children": [{"id": 2}]})
        ==
        Declarative2(id=1, text="abc", children=[Declarative1(id=2)])
    )

    dumper = retort.get_dumper(Declarative2)
    assert (
        dumper(Declarative2(id=1, text="abc", children=[Declarative1(id=2)]))
        ==
        {"id": 1, "text": "abc", "children": [{"id": 2, "parent_id": None}]}
    )
