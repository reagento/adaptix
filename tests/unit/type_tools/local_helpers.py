import operator
import typing
from functools import reduce
from typing import Union

from adaptix import TypeHint
from adaptix._internal.type_tools import BaseNormType, NormParamSpecMarker, NormTV, make_norm_type, normalize_type
from adaptix._internal.type_tools.normalize_type import Bound, NormParamSpec, NormTVTuple, NormTypeAlias


class UnionOpMaker:
    __name__ = "UnionOp"  # for test id generation

    def __getitem__(self, item):
        if isinstance(item, tuple):
            return reduce(operator.or_, item)
        return item


MISSING = object()


def nt_zero(origin, source=MISSING):
    if source is MISSING:
        source = origin
    return make_norm_type(origin, (), source=source)


def _norm_to_dict(obj):  # noqa: PLR0911
    if isinstance(obj, NormTV):
        return {
            "__type__": "NormTV",
            "variance": obj.variance,
            "limit": (
                _norm_to_dict(obj.limit.value)
                if isinstance(obj.limit, Bound) else
                [_norm_to_dict(el) for el in obj.limit.value]
            ),
            "source": obj.source,
            "default": obj.default,
        }
    if isinstance(obj, NormTVTuple):
        return {
            "__type__": "NormTVTuple",
            "source": obj.source,
            "default": obj.default,
        }
    if isinstance(obj, NormParamSpec):
        return {
            "__type__": "NormParamSpec",
            "limit": (
                _norm_to_dict(obj.limit.value)
                if isinstance(obj.limit, Bound) else
                [_norm_to_dict(el) for el in obj.limit.value]
            ),
            "source": obj.source,
            "default": obj.default,
        }
    if isinstance(obj, NormParamSpecMarker):
        return {
            "__type__": "NormParamSpecMarker",
            "origin": obj.origin,
            "param_spec": obj.param_spec,
        }
    if isinstance(obj, NormTypeAlias):
        return {
            "__type__": "NormTypeAlias",
            "origin": obj.origin,
            "args": [_norm_to_dict(arg) for arg in obj.args],
            "type_params": [_norm_to_dict(el) for el in obj.type_params],
        }
    if isinstance(obj, BaseNormType):
        result = {
            "__type__": "BaseNormType",
            "origin": obj.origin,
            "args": [_norm_to_dict(arg) for arg in obj.args],
            "source": obj.source,
        }
        if obj.origin == Union:
            result.pop("source")
        return result
    return obj


def assert_strict_equal(left: BaseNormType, right: BaseNormType):
    assert _norm_to_dict(left) == _norm_to_dict(right)
    assert left == right
    hash(left)
    hash(right)


def assert_normalize(tp: TypeHint, origin: TypeHint, args: list[typing.Hashable]):
    assert_strict_equal(
        normalize_type(tp),
        make_norm_type(origin, tuple(args), source=tp),
    )
