from typing import Optional, TypeVar, Union

from ...model_tools import DefaultFactory, DefaultValue
from .crown_definitions import Sieve

as_is_stub = lambda x: x  # noqa: E731  # pylint: disable=unnecessary-lambda-assignment


S = TypeVar('S', bound=Sieve)


_DEFAULT_CLAUSE_ATTR_NAME = '_adaptix_default_clause'


def set_default_clause(sieve: S, default: Union[DefaultValue, DefaultFactory]) -> S:
    setattr(sieve, _DEFAULT_CLAUSE_ATTR_NAME, default)
    return sieve


def get_default_clause(sieve: Sieve) -> Optional[Union[DefaultValue, DefaultFactory]]:
    return getattr(sieve, '_adaptix_default_clause', None)
