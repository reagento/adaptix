from typing import Optional
from unittest.mock import ANY

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship
from tests_helpers import requires

from adaptix._internal.feature_requirement import HAS_ANNOTATED
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
from adaptix._internal.model_tools.introspection.sqlalchemy import get_sqlalchemy_shape


def default_factory():
    return 2


def test_declarative():
    mapper_registry = registry()

    @mapper_registry.mapped
    class Declarative1:
        __tablename__ = "DeclarativeModel1"

        id: Mapped[int] = mapped_column(primary_key=True)

    @mapper_registry.mapped
    class Declarative2:
        __tablename__ = "DeclarativeModel2"

        id: Mapped[int] = mapped_column(primary_key=True)
        text: Mapped[str]
        nullable_field: Mapped[Optional[int]]
        field_with_default: Mapped[int] = mapped_column(default=2)
        field_with_default_factory: Mapped[int] = mapped_column(default=default_factory)
        field_with_default_context_factory: Mapped[int] = mapped_column(default=lambda ctx: 2)
        field_with_old_syntax = Column(String(), nullable=False)
        nullable_field_with_old_syntax = Column(Integer(), nullable=True)

        parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey(Declarative1.id))
        parent: Mapped[Optional[Declarative1]] = relationship()

    assert (
        get_sqlalchemy_shape(Declarative2)
        ==
        Shape(
            input=InputShape(
                constructor=Declarative2,
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
                        id="parent_id",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=Optional[Declarative1],
                        id="parent",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY,
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
                        field_id='parent_id',
                        name='parent_id',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='parent',
                        name='parent',
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
                        accessor=create_attr_accessor('nullable_field', is_required=True),
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
                        accessor=create_attr_accessor('nullable_field_with_old_syntax', is_required=True),
                    ),
                    OutputField(
                        type=Optional[int],
                        id="parent_id",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('parent_id', is_required=True),
                    ),
                    OutputField(
                        type=Optional[Declarative1],
                        id="parent",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('parent', is_required=True),
                    ),
                ),
                overriden_types=frozenset()
            )
        )
    )


def test_imperative():
    mapper_registry = registry()

    imperative_table1 = Table(
        "Imperative1",
        mapper_registry.metadata,
        Column("id", Integer, primary_key=True),
    )

    imperative_table2 = Table(
        "Imperative2",
        mapper_registry.metadata,
        Column("id", Integer, primary_key=True),
        Column("text", String, nullable=False),
        Column("nullable_field", Integer, nullable=True),
        Column("field_with_default", Integer, nullable=False, default=2),
        Column("field_with_default_factory", Integer, nullable=False, default=default_factory),
        Column("field_with_default_context_factory", Integer, nullable=False, default=lambda ctx: 2),
        Column("parent_id", ForeignKey(imperative_table1.c.id), nullable=False),
    )

    class Imperative1:
        pass

    class Imperative2:
        pass

    mapper_registry.map_imperatively(
        Imperative1,
        imperative_table1,
    )

    mapper_registry.map_imperatively(
        Imperative2,
        imperative_table2,
        properties={
            "parent": relationship(Imperative1)
        }
    )

    assert (
        get_sqlalchemy_shape(Imperative2)
        ==
        Shape(
            input=InputShape(
                constructor=Imperative2,
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
                        id='parent_id',
                        type=int,
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        is_required=False
                    ),
                    InputField(
                        type=Optional[Imperative1],
                        id="parent",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                ),
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
                        field_id='parent_id',
                        name='parent_id',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='parent',
                        name='parent',
                        kind=ParamKind.KW_ONLY
                    ),
                ),
                overriden_types=frozenset()
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
                        accessor=create_attr_accessor('nullable_field', is_required=True),
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
                        id='parent_id',
                        type=int,
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('parent_id', is_required=True)
                    ),
                    OutputField(
                        id='parent',
                        type=Optional[Imperative1],
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('parent', is_required=True),
                    )
                ),
                overriden_types=frozenset()
            )
        )
    )


@requires(HAS_ANNOTATED)
def test_declarative_annotated():
    from typing import Annotated

    mapper_registry = registry()

    @mapper_registry.mapped
    class Declarative1:
        __tablename__ = "DeclarativeModel1"

        id: Mapped[int] = mapped_column(primary_key=True)

    tp_id = Annotated[int, mapped_column(primary_key=True)]
    tp_field_with_default = Annotated[int, mapped_column(default=2)]
    tp_field_with_default_factory = Annotated[int, mapped_column(default=default_factory)]
    tp_field_with_default_context_factory = Annotated[int, mapped_column(default=lambda ctx: 2)]
    tp_parent_id = Annotated[Optional[int], mapped_column(ForeignKey(Declarative1.id))]

    @mapper_registry.mapped
    class Declarative2:
        __tablename__ = "DeclarativeModel2"

        id: Mapped[tp_id]
        field_with_default: Mapped[tp_field_with_default]
        field_with_default_factory: Mapped[tp_field_with_default_factory]
        field_with_default_context_factory: Mapped[tp_field_with_default_context_factory]
        parent_id: Mapped[tp_parent_id]
        parent: Mapped[Optional[Declarative1]] = relationship()

    assert (
        get_sqlalchemy_shape(Declarative2)
        ==
        Shape(
            input=InputShape(
                constructor=Declarative2,
                kwargs=None,
                fields=(
                    InputField(
                        type=tp_id,
                        id="id",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=tp_field_with_default,
                        id="field_with_default",
                        default=DefaultValue(2),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=tp_field_with_default_factory,
                        id="field_with_default_factory",
                        default=DefaultFactory(default_factory),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=tp_field_with_default_context_factory,
                        id="field_with_default_context_factory",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=tp_parent_id,
                        id="parent_id",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=Optional[Declarative1],
                        id="parent",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY,
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
                        field_id='parent_id',
                        name='parent_id',
                        kind=ParamKind.KW_ONLY,
                    ),
                    Param(
                        field_id='parent',
                        name='parent',
                        kind=ParamKind.KW_ONLY,
                    ),
                )
            ),
            output=OutputShape(
                fields=(
                    OutputField(
                        type=tp_id,
                        id="id",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('id', is_required=True),
                    ),
                    OutputField(
                        type=tp_field_with_default,
                        id="field_with_default",
                        default=DefaultValue(2),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('field_with_default', is_required=True),
                    ),
                    OutputField(
                        type=tp_field_with_default_factory,
                        id="field_with_default_factory",
                        default=DefaultFactory(default_factory),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('field_with_default_factory', is_required=True),
                    ),
                    OutputField(
                        type=tp_field_with_default_context_factory,
                        id="field_with_default_context_factory",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('field_with_default_context_factory', is_required=True),
                    ),
                    OutputField(
                        type=tp_parent_id,
                        id="parent_id",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('parent_id', is_required=True),
                    ),
                    OutputField(
                        type=Optional[Declarative1],
                        id="parent",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('parent', is_required=True),
                    ),
                ),
                overriden_types=frozenset()
            )
        )
    )
