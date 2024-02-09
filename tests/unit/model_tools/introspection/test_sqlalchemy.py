from typing import List, Optional
from unittest.mock import ANY

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship

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

mapper_registry = registry()


def default_factory():
    return 2


@mapper_registry.mapped
class Declarative:
    __tablename__ = "DeclarativeModel"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str]
    nullable_field: Mapped[Optional[int]]
    field_with_default: Mapped[int] = mapped_column(default=2)
    field_with_default_factory: Mapped[int] = mapped_column(default=default_factory)
    field_with_default_context_factory: Mapped[int] = mapped_column(default=lambda ctx: 2)
    field_with_old_syntax = Column(String(), nullable=False)
    nullable_field_with_old_syntax = Column(Integer(), nullable=True)

    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("Imperative.id"))
    parent: Mapped[Optional["Imperative"]] = relationship(
        "Imperative", back_populates="children"
    )


imperative_table = Table(
    "Imperative",
    mapper_registry.metadata,
    Column("id", Integer, primary_key=True)
)


class Imperative:
    pass


mapper_registry.map_imperatively(
    Imperative,
    imperative_table,
    properties={
        "children": relationship(Declarative, back_populates="parent")
    }
)


def test_shape_getter():
    assert (
        get_sqlalchemy_shape(Declarative)
        ==
        Shape(
            input=InputShape(
                constructor=Declarative,
                kwargs=None,
                fields=(
                    InputField(
                        type=Mapped[int],
                        id="id",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=Mapped[str],
                        id="text",
                        default=NoDefault(),
                        is_required=True,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=Mapped[Optional[int]],
                        id="nullable_field",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=Mapped[int],
                        id="field_with_default",
                        default=DefaultValue(2),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=Mapped[int],
                        id="field_with_default_factory",
                        default=DefaultFactory(default_factory),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=Mapped[int],
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
                        type=Mapped[Optional[int]],
                        id="parent_id",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=ANY
                    ),
                    InputField(
                        type=Mapped[Optional[Imperative]],
                        id="parent",
                        default=NoDefault(),
                        is_required=False,
                        metadata={},
                        original=Declarative.parent.property
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
                        type=Mapped[int],
                        id="id",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('id', is_required=True),
                    ),
                    OutputField(
                        type=Mapped[str],
                        id="text",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('text', is_required=True),
                    ),
                    OutputField(
                        type=Mapped[Optional[int]],
                        id="nullable_field",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('nullable_field', is_required=False),
                    ),
                    OutputField(
                        type=Mapped[int],
                        id="field_with_default",
                        default=DefaultValue(2),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('field_with_default', is_required=True),
                    ),
                    OutputField(
                        type=Mapped[int],
                        id="field_with_default_factory",
                        default=DefaultFactory(default_factory),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('field_with_default_factory', is_required=True),
                    ),
                    OutputField(
                        type=Mapped[int],
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
                        type=Mapped[Optional[int]],
                        id="parent_id",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('parent_id', is_required=False),
                    ),
                    OutputField(
                        type=Mapped[Optional[Imperative]],
                        id="parent",
                        default=NoDefault(),
                        metadata={},
                        original=Declarative.parent.property,
                        accessor=create_attr_accessor('parent', is_required=False),
                    ),
                ),
                overriden_types=frozenset()
            )
        )
    )

    assert (
        get_sqlalchemy_shape(Imperative)
        ==
        Shape(
            input=InputShape(
                constructor=Imperative,
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
                        type=List[Declarative],
                        id="children",
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
                        field_id='children',
                        name='children',
                        kind=ParamKind.KW_ONLY,
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
                        type=List[Declarative],
                        id="children",
                        default=NoDefault(),
                        metadata={},
                        original=ANY,
                        accessor=create_attr_accessor('children', is_required=True),
                    ),
                ),
                overriden_types=frozenset()
            )
        )
    )
