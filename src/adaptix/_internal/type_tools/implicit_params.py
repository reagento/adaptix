import collections
import re
import sys
import typing
from typing import Any, ForwardRef, TypeVar, Union, get_args

from ..common import TypeHint, VarTuple
from ..feature_requirement import HAS_PARAM_SPEC
from .basic_utils import create_union, eval_forward_ref, is_user_defined_generic, strip_alias


class ImplicitParamsGetter:
    ONE_ANY_STR_PARAM = [re.Pattern, re.Match]

    TYPE_PARAM_COUNT = {
        type: 1,
        list: 1,
        set: 1,
        frozenset: 1,
        collections.Counter: 1,
        collections.deque: 1,
        dict: 2,
        collections.defaultdict: 2,
        collections.OrderedDict: 2,
        collections.ChainMap: 2,
        **{el: 1 for el in ONE_ANY_STR_PARAM}
    }

    def _process_limit_element(self, type_var: TypeVar, tp: TypeHint) -> TypeHint:
        if isinstance(tp, ForwardRef):
            return eval_forward_ref(vars(sys.modules[type_var.__module__]), tp)
        return tp

    def _process_type_var(self, type_var: TypeVar) -> TypeHint:
        if HAS_PARAM_SPEC and isinstance(type_var, typing.ParamSpec):
            return ...
        if type_var.__constraints__:
            return create_union(
                tuple(
                    self._process_limit_element(type_var, constraint)
                    for constraint in type_var.__constraints__
                )
            )
        if type_var.__bound__ is None:
            return Any
        return self._process_limit_element(type_var, type_var.__bound__)

    def get_implicit_params(self, origin) -> VarTuple[TypeHint]:
        if origin in self.ONE_ANY_STR_PARAM:
            return (Union[str, bytes], )

        if is_user_defined_generic(origin):
            return tuple(
                self._process_type_var(param)
                for param in origin.__parameters__
            )

        count = self.TYPE_PARAM_COUNT.get(origin, 0)
        return tuple(Any for _ in range(count))


def fill_implicit_params(tp: TypeHint) -> TypeHint:
    if get_args(tp):
        raise ValueError(f'{tp} is not a generic')

    params = ImplicitParamsGetter().get_implicit_params(strip_alias(tp))
    if params:
        return tp[params]
    raise ValueError(f'{tp} is not a generic')
