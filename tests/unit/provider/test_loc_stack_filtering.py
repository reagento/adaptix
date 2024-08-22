# ruff: noqa: A001, A002
import collections.abc
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Annotated, Any, Dict, Generic, Iterable, List, Optional, Type, TypeVar, Union, overload

import pytest
from tests_helpers import full_match
from tests_helpers.misc import create_mediator

from adaptix import Chain, P, Retort, loader
from adaptix._internal.common import TypeHint
from adaptix._internal.model_tools.definitions import NoDefault
from adaptix._internal.provider.loc_stack_filtering import (
    ExactOriginLSC,
    ExactTypeLSC,
    LocStack,
    LocStackEndChecker,
    OriginSubclassLSC,
    create_loc_stack_checker,
)
from adaptix._internal.provider.location import FieldLoc, GenericParamLoc, TypeHintLoc
from adaptix._internal.type_tools import normalize_type


@overload
def param_result(*values: Any, id: Optional[str] = None, result: Any):
    ...


@overload
def param_result(*values: Any, id: Optional[str] = None, raises: Type[Exception]):
    ...


@overload
def param_result(*values: Any, id: Optional[str] = None, raises: Type[Exception], exact_match: str):
    ...


@overload
def param_result(*values: Any, id: Optional[str] = None, raises: Type[Exception], match: str):
    ...


def param_result(*values, result=None, raises=None, exact_match=None, match=None, id=None):
    if raises is not None:
        context = pytest.raises(
            raises, match=full_match(exact_match) if exact_match is not None else match,
        )
    else:
        context = None
    if id is None:
        id = str(values[0]) if len(values) == 1 else str(values)
    return pytest.param(*values, result, context, id=id)


@pytest.mark.parametrize(
    ["loc_stack", "result", "context"],
    [
        param_result(
            LocStack(
                TypeHintLoc(int),
            ),
            result=False,
            id="1-item",
        ),
        param_result(
            LocStack(
                TypeHintLoc(int),
                TypeHintLoc(str),
            ),
            result=False,
            id="2-items",
        ),
        param_result(
            LocStack(
                TypeHintLoc(int),
                TypeHintLoc(str),
                TypeHintLoc(bool),
            ),
            result=True,
            id="ok",
        ),
        param_result(
            LocStack(
                TypeHintLoc(int),
                TypeHintLoc(str),
                TypeHintLoc(str),
            ),
            result=False,
            id="last-is-bad",
        ),
        param_result(
            LocStack(
                TypeHintLoc(int),
                TypeHintLoc(int),
                TypeHintLoc(str),
                TypeHintLoc(bool),
            ),
            result=True,
            id="extra-stack-matched-with-prev",
        ),
        param_result(
            LocStack(
                TypeHintLoc(str),
                TypeHintLoc(int),
                TypeHintLoc(str),
                TypeHintLoc(bool),
            ),
            result=True,
            id="extra-stack",
        ),
    ],
)
def test_stack_end_rc(loc_stack, result, context):
    checker = LocStackEndChecker(
        [
            create_loc_stack_checker(int),
            create_loc_stack_checker(str),
            create_loc_stack_checker(bool),
        ],
    )
    assert checker.check_loc_stack(create_mediator(), loc_stack) == result


@pytest.mark.parametrize(
    ["loc_stack", "result", "context"],
    [
        param_result(
            LocStack(
                TypeHintLoc(bool),
                TypeHintLoc(int),
                TypeHintLoc(str),
                TypeHintLoc(bool),
            ),
            result=True,
            id="ok",
        ),
        param_result(
            LocStack(
                TypeHintLoc(int),
                TypeHintLoc(str),
                TypeHintLoc(bool),
            ),
            result=False,
            id="too-small",
        ),
        param_result(
            LocStack(
                TypeHintLoc(str),
                TypeHintLoc(int),
                TypeHintLoc(str),
                TypeHintLoc(bool),
            ),
            result=False,
            id="bad",
        ),
    ],
)
def test_nested_start_rc(loc_stack, result, context):
    checker = LocStackEndChecker(
        [
            P.ANY,
            LocStackEndChecker(
                [
                    create_loc_stack_checker(bool),
                    create_loc_stack_checker(int),
                    create_loc_stack_checker(str),
                ],
            ),
            create_loc_stack_checker(bool),
        ],
    )
    assert checker.check_loc_stack(create_mediator(), loc_stack) == result


@dataclass
class WithUserName:
    user_name: str


def field_loc_map(name: str, tp: TypeHint) -> FieldLoc:
    return FieldLoc(
        type=tp,
        field_id=name,
        default=NoDefault(),
        metadata={},
    )


@pytest.mark.parametrize(
    ["pattern", "loc_stack", "result", "context"],
    [
        param_result(
            P[int],
            LocStack(TypeHintLoc(int)),
            result=True,
            id="int-ok",
        ),
        param_result(
            P[int],
            LocStack(TypeHintLoc(str)),
            result=False,
            id="int-fail",
        ),
        param_result(
            P[WithUserName].user_name,
            LocStack(
                TypeHintLoc(WithUserName),
                field_loc_map("user_name", str),
            ),
            result=True,
            id="model-attr-ok-1",
        ),
        param_result(
            P[WithUserName].user_name,
            LocStack(
                TypeHintLoc(WithUserName),
                field_loc_map("user_name", int),
            ),
            result=True,
            id="model-attr-ok-2",
        ),
        param_result(
            P[WithUserName].user_id,
            LocStack(
                TypeHintLoc(WithUserName),
                field_loc_map("user_name", int),
            ),
            result=False,
            id="model-attr-fail",
        ),
        param_result(
            P[WithUserName] + P.user_name,
            LocStack(
                TypeHintLoc(WithUserName),
                field_loc_map("user_name", int),
            ),
            result=True,
            id="model-attr-ok-concat",
        ),
        param_result(
            P[Dict].generic_arg(0, str),
            LocStack(
                TypeHintLoc(Dict),
                GenericParamLoc(str, 0),
            ),
            result=True,
            id="generic-arg-ok",
        ),
        param_result(
            P[Dict].generic_arg(0, str),
            LocStack(
                TypeHintLoc(Dict),
                GenericParamLoc(str, 1),
            ),
            result=False,
            id="generic-arg-fail",
        ),
    ],
)
def test_request_pattern(pattern, loc_stack, result, context):
    assert pattern.build_loc_stack_checker().check_loc_stack(create_mediator(), loc_stack) == result


def test_generic_pattern_create_fail():
    with pytest.raises(
        TypeError,
        match=full_match(
            "Can not use LocStackPattern as predicate inside LocStackPattern."
            " If you want to combine several LocStackPattern, you can use `+` operator",
        ),
    ):
        P[WithUserName][P.user_name]


def plus_one(data):
    return data + 1


def plus_two(data):
    return data + 2


def test_request_pattern_generic_arg_dict_override():
    retort = Retort(
        recipe=[
            loader(P[Dict].generic_arg(0, int), plus_one, Chain.LAST),
            loader(P[Dict].generic_arg(1, int), plus_two, Chain.LAST),
        ],
    )

    loaded_dict = retort.load({10: 20}, Dict[int, int])
    assert loaded_dict == {11: 22}


T = TypeVar("T")


class MyGeneric(Generic[T]):
    pass


@pytest.mark.parametrize(
    ["value", "result", "context"],
    [
        param_result(
            int,
            result=ExactOriginLSC(int),
        ),
        param_result(
            List,
            result=ExactOriginLSC(list),
        ),
        param_result(
            dict,
            result=ExactOriginLSC(dict),
        ),
        param_result(
            Iterable,
            result=OriginSubclassLSC(collections.abc.Iterable),
        ),
        param_result(
            Iterable[int],
            result=ExactTypeLSC(normalize_type(Iterable[int])),
        ),
        param_result(
            List[int],
            result=ExactTypeLSC(normalize_type(List[int])),
        ),
        param_result(
            List[T],
            raises=ValueError,
            exact_match="Can not create LocStackChecker from typing.List[~T] generic alias (parametrized generic)",
        ),
        param_result(
            Union,
            result=ExactOriginLSC(Union),
        ),
        param_result(
            Annotated,
            result=ExactOriginLSC(Annotated),
        ),
        param_result(
            Annotated[int, "meta"],
            result=ExactTypeLSC(normalize_type(Annotated[int, "meta"])),
        ),
        param_result(
            Annotated[List[int], "meta"],
            result=ExactTypeLSC(normalize_type(Annotated[list[int], "meta"])),
        ),
        param_result(
            Annotated[list, "meta"],
            raises=ValueError,
            exact_match=(
                "Can not create LocStackChecker from"
                " typing.Annotated[list, 'meta'] generic alias (parametrized generic)"
            ),
        ),
        param_result(
            Annotated[List[T], "meta"],
            raises=ValueError,
            exact_match=(
                "Can not create LocStackChecker from"
                " typing.Annotated[typing.List[~T], 'meta'] generic alias (parametrized generic)"
            ),
        ),
        param_result(
            Annotated[Dict[int, T], "meta"],
            raises=ValueError,
            exact_match=(
                "Can not create LocStackChecker from"
                " typing.Annotated[typing.Dict[int, ~T], 'meta'] generic alias (parametrized generic)"
            ),
        ),
    ],
)
def test_create_request_checker(value, result, context):
    with context or nullcontext():
        assert create_loc_stack_checker(value) == result
