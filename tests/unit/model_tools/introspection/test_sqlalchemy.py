from typing import List, Optional
from unittest.mock import ANY

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

from adaptix._internal.model_tools.definitions import (
    DefaultFactory,
    DefaultValue,
    InputField,
    InputShape,
    NoDefault,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    Shape,
    create_attr_accessor,
)
from adaptix._internal.model_tools.introspection.sqlalchemy_tables import get_sqlalchemy_shape

Base = declarative_base()


def default_factory():
    return 2


class MyTable(Base):
    __tablename__ = "MyTable"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str]
    nullable_field: Mapped[Optional[int]]
    field_with_default: Mapped[int] = mapped_column(default=2)
    field_with_default_factory: Mapped[int] = mapped_column(default=default_factory)
    field_with_default_context_factory: Mapped[int] = mapped_column(default=lambda ctx: 2)
    field_with_old_syntax = Column(String(), nullable=False)
    nullable_field_with_old_syntax = Column(Integer(), nullable=True)

    fk_id: Mapped[Optional[int]] = mapped_column(ForeignKey("MyTableFK.id"))
    fk: Mapped[Optional["MyTableFK"]] = relationship(
        "MyTableFK", back_populates="my_table_objs"
    )


class MyTableFK(Base):
    __tablename__ = "MyTableFK"

    id: Mapped[int] = mapped_column(primary_key=True)
    my_table_objs: Mapped[List[MyTable]] = relationship(
        MyTable, back_populates="fk"
    )


def test_shape_getter():
    assert (
        get_sqlalchemy_shape(MyTable)
        ==
        Shape(
            input=InputShape(
                constructor=MyTable,
                kwargs=None,
                fields=(
                    InputField(
                        type=int,
                        id="id",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=str,
                        id="text",
                        default=NoDefault(),
                        is_required=True,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=Optional[int],
                        id="nullable_field",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=int,
                        id="field_with_default",
                        default=DefaultValue(2),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=int,
                        id="field_with_default_factory",
                        default=DefaultFactory(default_factory),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=int,
                        id="field_with_default_context_factory",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=str,
                        id="field_with_old_syntax",
                        default=NoDefault(),
                        is_required=True,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=Optional[int],
                        id="nullable_field_with_old_syntax",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=Optional[int],
                        id="fk_id",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=Optional[MyTableFK],
                        id="fk",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=MyTable.fk.property
                    ),
                ),
                overriden_types=frozenset(),
                params=(
                    Param(
                        field_id='id',
                        name='id',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='text',
                        name='text',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='nullable_field',
                        name='nullable_field',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='field_with_default',
                        name='field_with_default',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='field_with_default_factory',
                        name='field_with_default_factory',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='field_with_default_context_factory',
                        name='field_with_default_context_factory',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='field_with_old_syntax',
                        name='field_with_old_syntax',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='nullable_field_with_old_syntax',
                        name='nullable_field_with_old_syntax',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='fk_id',
                        name='fk_id',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='fk',
                        name='fk',
                        kind=ParamKind.KW_ONLY,
                    ),
                )
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=int,
                        id="id",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('id', is_required=True),
                    ),
                    OutputField(
                        type=str,
                        id="text",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('text', is_required=True),
                    ),
                    OutputField(
                        type=Optional[int],
                        id="nullable_field",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('nullable_field', is_required=False),
                    ),
                    OutputField(
                        type=int,
                        id="field_with_default",
                        default=DefaultValue(2),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('field_with_default', is_required=True),
                    ),
                    OutputField(
                        type=int,
                        id="field_with_default_factory",
                        default=DefaultFactory(default_factory),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('field_with_default_factory', is_required=True),
                    ),
                    OutputField(
                        type=int,
                        id="field_with_default_context_factory",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('field_with_default_context_factory', is_required=True),
                    ),
                    OutputField(
                        type=str,
                        id="field_with_old_syntax",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('field_with_old_syntax', is_required=True),
                    ),
                    OutputField(
                        type=Optional[int],
                        id="nullable_field_with_old_syntax",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('nullable_field_with_old_syntax', is_required=False),
                    ),
                    OutputField(
                        type=Optional[int],
                        id="fk_id",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('fk_id', is_required=False),
                    ),
                    OutputField(
                        type=Optional[MyTableFK],
                        id="fk",
                        default=NoDefault(),
                        metadata={},
                        original=MyTable.fk.property,
                        accessor=create_attr_accessor('fk', is_required=False),
                    ),
                ),
                overriden_types=frozenset()
            )
        )
    )
