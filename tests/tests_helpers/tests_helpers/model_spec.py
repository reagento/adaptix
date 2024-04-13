from dataclasses import dataclass
from enum import Enum
from operator import getitem
from types import ModuleType
from typing import Any, Callable, Mapping, NamedTuple, TypedDict, Union

import pytest
from _pytest.python import Metafunc

from adaptix._internal.feature_requirement import (
    HAS_ATTRS_PKG,
    HAS_PY_311,
    HAS_PYDANTIC_PKG,
    HAS_SQLALCHEMY_PKG,
    Requirement,
)
from adaptix._internal.type_tools import get_all_type_hints

from .misc import FailedRequirement


def sqlalchemy_equals(self, other):
    if type(self) is not type(other):
        return False

    self_state = vars(self).copy()
    self_state.pop("_sa_instance_state")
    other_state = vars(other).copy()
    other_state.pop("_sa_instance_state")
    return self_state == other_state


class ModelSpec(Enum):
    DATACLASS = "dataclass"
    TYPED_DICT = "typed_dict"
    NAMED_TUPLE = "named_tuple"
    ATTRS = "attrs"
    SQLALCHEMY = "sqlalchemy"
    PYDANTIC = "pydantic"

    @classmethod
    def default_requirements(cls):
        return {
            cls.ATTRS: HAS_ATTRS_PKG,
            cls.SQLALCHEMY: HAS_SQLALCHEMY_PKG,
            cls.PYDANTIC: HAS_PYDANTIC_PKG,
        }


@dataclass
class ModelSpecSchema:
    decorator: Any
    bases: Any
    get_field: Callable[[Any, str], Any]
    kind: ModelSpec


def create_sqlalchemy_decorator():
    from sqlalchemy import String
    from sqlalchemy.orm import Mapped, mapped_column, registry
    from sqlalchemy.sql.base import NO_ARG

    def sqlalchemy_decorator(cls):
        reg = registry()

        cls.__tablename__ = cls.__name__
        cls.__annotations__ = {
            key: Mapped[value]
            for key, value in get_all_type_hints(cls).items()
        }
        for idx, key in enumerate(cls.__annotations__.keys()):
            setattr(
                cls,
                key,
                mapped_column(
                    String(),
                    primary_key=idx == 0,
                    default=getattr(cls, key) if hasattr(cls, key) else NO_ARG,
                ),
            )

        cls.__eq__ = sqlalchemy_equals
        return reg.mapped(cls)

    return sqlalchemy_decorator


def model_spec_to_schema(spec: ModelSpec):
    if spec == ModelSpec.DATACLASS:
        return ModelSpecSchema(decorator=dataclass, bases=(), get_field=getattr, kind=spec)
    if spec == ModelSpec.TYPED_DICT:
        return ModelSpecSchema(decorator=lambda x: x, bases=(TypedDict,), get_field=getitem, kind=spec)
    if spec == ModelSpec.NAMED_TUPLE:
        return ModelSpecSchema(decorator=lambda x: x, bases=(NamedTuple,), get_field=getattr, kind=spec)
    if spec == ModelSpec.ATTRS:
        from attrs import define
        return ModelSpecSchema(decorator=define, bases=(), get_field=getattr, kind=spec)
    if spec == ModelSpec.SQLALCHEMY:
        return ModelSpecSchema(decorator=create_sqlalchemy_decorator(), bases=(), get_field=getattr, kind=spec)
    if spec == ModelSpec.PYDANTIC:
        from pydantic import BaseModel, ConfigDict

        class CustomBaseModel(BaseModel):
            model_config = ConfigDict(arbitrary_types_allowed=True)

        return ModelSpecSchema(decorator=lambda x: x, bases=(CustomBaseModel, ), get_field=getattr, kind=spec)
    raise ValueError


def exclude_model_spec(first_spec: ModelSpec, *other_specs: ModelSpec):
    specs = [first_spec, *other_specs]

    def decorator(func):
        func.adaptix_exclude_model_spec = specs
        return func

    return decorator


def only_model_spec(first_spec: ModelSpec, *other_specs: ModelSpec):
    specs = [first_spec, *other_specs]
    return exclude_model_spec(*[model_spec for model_spec in ModelSpec if model_spec not in specs])


def with_model_spec_requirement(requirements: Mapping[ModelSpec, Requirement]):
    def decorator(func):
        func.adaptix_model_spec_requirements = requirements
        return func

    return decorator


GENERIC_MODELS_REQUIREMENTS: Mapping[ModelSpec, Requirement] = {
    ModelSpec.TYPED_DICT: HAS_PY_311,
    ModelSpec.NAMED_TUPLE: HAS_PY_311,
    ModelSpec.SQLALCHEMY: FailedRequirement("SQLAlchemy models can not be generic"),
}


def only_generic_models(obj: Union[Callable, ModuleType]):
    obj.adaptix_model_spec_requirements = GENERIC_MODELS_REQUIREMENTS
    return obj


def parametrize_model_spec(fixture_name: str, metafunc: Metafunc) -> None:
    if fixture_name not in metafunc.fixturenames:
        return

    excluded = getattr(metafunc.function, "adaptix_exclude_model_spec", [])
    requirements = {
        **ModelSpec.default_requirements(),
        **getattr(metafunc.module, "adaptix_model_spec_requirements", {}),
        **getattr(metafunc.function, "adaptix_model_spec_requirements", {}),
    }
    metafunc.parametrize(
        fixture_name,
        [
            pytest.param(model_spec_to_schema(spec), id=spec.value)
            for spec in ModelSpec
            if spec not in excluded and (spec not in requirements or bool(requirements[spec]))
        ],
    )
