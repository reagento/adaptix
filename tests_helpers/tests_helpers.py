from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Callable, Iterable, List, Optional, Type, TypeVar, Union

import pytest

from dataclass_factory_30.common import EllipsisType, VarTuple
from dataclass_factory_30.feature_requirement import PythonVersionRequirement
from dataclass_factory_30.provider import CannotProvide, Mediator, Provider, Request
from dataclass_factory_30.provider.model.basic_gen import CodeGenAccumulator
from dataclass_factory_30.retort import OperatingRetort
from dataclass_factory_30.struct_path import get_path

T = TypeVar("T")


def requires(requirement: PythonVersionRequirement):
    ver_str = '.'.join(map(str, requirement.min_version))

    def wrapper(func):
        return pytest.mark.skipif(
            not requirement,
            reason=f'Need Python >= {ver_str}'
        )(func)

    return wrapper


class TestRetort(OperatingRetort):
    def __init__(self, recipe: Iterable[Provider]):
        super().__init__(recipe)

    def _get_config_recipe(self) -> VarTuple[Provider]:
        return ()

    provide = OperatingRetort._facade_provide


E = TypeVar('E', bound=Exception)


def raises_path(
    exc: Union[Type[E], E],
    func: Callable[[], Any],
    *,
    path: Union[list, None, EllipsisType] = Ellipsis,
    match: Optional[str] = None,
) -> E:
    exc_type = exc if isinstance(exc, type) else type(exc)

    with pytest.raises(exc_type, match=match) as exc_info:
        func()

    assert exc_type == exc_info.type

    if not isinstance(exc, type):
        if is_dataclass(exc):
            assert asdict(exc_info.value) == asdict(exc)  # noqa
        else:
            raise TypeError("Can compare only dataclass instances")

    if not isinstance(path, EllipsisType):
        extracted_path = get_path(exc_info.value)
        if path is None:
            assert extracted_path is None
        else:
            assert extracted_path is not None
            assert list(extracted_path) == list(path)

    return exc_info.value


def parametrize_bool(param: str, *params: str):
    full_params = [param, *params]

    def decorator(func):
        for p in full_params:
            func = pytest.mark.parametrize(
                p, [False, True],
                ids=[f'{p}=False', f'{p}=True']
            )(func)
        return func

    return decorator


@dataclass
class DebugCtx:
    accum: CodeGenAccumulator

    @property
    def source(self):
        return self.accum.list[-1][1].source

    @property
    def source_namespace(self):
        return self.accum.list[-1][1].namespace


@dataclass
class PlaceholderProvider(Provider):
    value: int

    def apply_provider(self, mediator: Mediator, request: Request[T]) -> T:
        raise CannotProvide
