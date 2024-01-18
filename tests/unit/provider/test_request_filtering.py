import collections.abc
import typing
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any, Dict, Generic, Iterable, List, Optional, Type, TypeVar, Union, overload

import pytest
from tests_helpers import cond_list, full_match_regex_str

from adaptix import CannotProvide, Chain, P, Retort, loader
from adaptix._internal.common import TypeHint
from adaptix._internal.feature_requirement import HAS_ANNOTATED
from adaptix._internal.model_tools.definitions import NoDefault
from adaptix._internal.provider.request_cls import (
    FieldLoc,
    GenericParamLoc,
    LocatedRequest,
    LocMap,
    LocStack,
    TypeHintLoc,
)
from adaptix._internal.provider.request_filtering import (
    AnyRequestChecker,
    ExactOriginRC,
    ExactTypeRC,
    LocStackEndRC,
    OriginSubclassRC,
    create_request_checker,
)
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
            raises, match=full_match_regex_str(exact_match) if exact_match is not None else match
        )
    else:
        context = None
    if id is None:
        if len(values) == 1:
            id = str(values[0])
        else:
            id = str(values)
    return pytest.param(*values, result, context, id=id)


def create_mediator():
    return Retort()._create_mediator()


@pytest.mark.parametrize(
    ['request_obj', 'result', 'context'],
    [
        param_result(
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(int)),
                )
            ),
            raises=CannotProvide,
            exact_match="LocStack is too small",
            id='1-item',
        ),
        param_result(
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(int)),
                    LocMap(TypeHintLoc(str)),
                )
            ),
            raises=CannotProvide,
            exact_match="LocStack is too small",
            id='2-items',
        ),
        param_result(
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(int)),
                    LocMap(TypeHintLoc(str)),
                    LocMap(TypeHintLoc(bool)),
                )
            ),
            result=None,
            id='ok',
        ),
        param_result(
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(int)),
                    LocMap(TypeHintLoc(str)),
                    LocMap(TypeHintLoc(str)),
                )
            ),
            raises=CannotProvide,
            id='last-is-bad',
        ),
        param_result(
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(int)),
                    LocMap(TypeHintLoc(int)),
                    LocMap(TypeHintLoc(str)),
                    LocMap(TypeHintLoc(bool)),
                )
            ),
            result=None,
            id='extra-stack-matched-with-prev',
        ),
        param_result(
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(str)),
                    LocMap(TypeHintLoc(int)),
                    LocMap(TypeHintLoc(str)),
                    LocMap(TypeHintLoc(bool)),
                )
            ),
            result=None,
            id='extra-stack',
        ),
    ],
)
def test_stack_end_rc(request_obj, result, context):
    checker = LocStackEndRC(
        [
            create_request_checker(int),
            create_request_checker(str),
            create_request_checker(bool),
        ]
    )
    with context or nullcontext():
        assert checker.check_request(
            create_mediator(),
            request_obj,
        ) == result


@pytest.mark.parametrize(
    ['request_obj', 'result', 'context'],
    [
        param_result(
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(bool)),
                    LocMap(TypeHintLoc(int)),
                    LocMap(TypeHintLoc(str)),
                    LocMap(TypeHintLoc(bool)),
                )
            ),
            result=None,
            id='ok',
        ),
        param_result(
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(int)),
                    LocMap(TypeHintLoc(str)),
                    LocMap(TypeHintLoc(bool)),
                )
            ),
            raises=CannotProvide,
            exact_match="LocStack is too small",
            id='too-small',
        ),
        param_result(
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(str)),
                    LocMap(TypeHintLoc(int)),
                    LocMap(TypeHintLoc(str)),
                    LocMap(TypeHintLoc(bool)),
                )
            ),
            raises=CannotProvide,
            id='bad',
        ),
    ],
)
def test_nested_start_rc(request_obj, result, context):
    checker = LocStackEndRC(
        [
            AnyRequestChecker(),
            LocStackEndRC(
                [
                    create_request_checker(bool),
                    create_request_checker(int),
                    create_request_checker(str),
                ]
            ),
            create_request_checker(bool),
        ]
    )
    with context or nullcontext():
        assert checker.check_request(
            create_mediator(),
            request_obj,
        ) == result


@dataclass
class WithUserName:
    user_name: str


def field_loc_map(name: str, tp: TypeHint) -> LocMap:
    return LocMap(
        TypeHintLoc(tp),
        FieldLoc(
            field_id=name,
            default=NoDefault(),
            metadata={},
        )
    )


@pytest.mark.parametrize(
    ['pattern', 'request_obj', 'result', 'context'],
    [
        param_result(
            P[int],
            LocatedRequest(loc_stack=LocStack(LocMap(TypeHintLoc(int)))),
            result=None,
            id='int-ok',
        ),
        param_result(
            P[int],
            LocatedRequest(loc_stack=LocStack(LocMap(TypeHintLoc(str)))),
            raises=CannotProvide,
            id='int-fail',
        ),
        param_result(
            P[WithUserName].user_name,
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(WithUserName)),
                    field_loc_map('user_name', str),
                )
            ),
            result=None,
            id='model-attr-ok-1',
        ),
        param_result(
            P[WithUserName].user_name,
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(WithUserName)),
                    field_loc_map('user_name', int),
                )
            ),
            result=None,
            id='model-attr-ok-2',
        ),
        param_result(
            P[WithUserName].user_id,
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(WithUserName)),
                    field_loc_map('user_name', int),
                )
            ),
            raises=CannotProvide,
            id='model-attr-fail',
        ),
        param_result(
            P[WithUserName] + P.user_name,
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(WithUserName)),
                    field_loc_map('user_name', int),
                )
            ),
            result=None,
            id='model-attr-ok-concat',
        ),
        param_result(
            P[Dict].generic_arg(0, str),
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(Dict)),
                    LocMap(TypeHintLoc(str), GenericParamLoc(0)),
                )
            ),
            result=None,
            id='generic-arg-ok',
        ),
        param_result(
            P[Dict].generic_arg(0, str),
            LocatedRequest(
                loc_stack=LocStack(
                    LocMap(TypeHintLoc(Dict)),
                    LocMap(TypeHintLoc(str), GenericParamLoc(1)),
                )
            ),
            raises=CannotProvide,
            id='generic-arg-fail',
        ),
    ],
)
def test_request_pattern(pattern, request_obj, result, context):
    with context or nullcontext():
        assert pattern.build_request_checker().check_request(
            create_mediator(),
            request_obj,
        ) == result


def test_generic_pattern_create_fail():
    with pytest.raises(
        TypeError,
        match=full_match_regex_str(
            'Can not use RequestPattern as predicate inside RequestPattern.'
            ' If you want to combine several RequestPattern, you can use `+` operator'
        )
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
        ]
    )

    loaded_dict = retort.load({10: 20}, Dict[int, int])
    assert loaded_dict == {11: 22}


T = TypeVar('T')


class MyGeneric(Generic[T]):
    pass


@pytest.mark.parametrize(
    ['value', 'result', 'context'],
    [
        param_result(
            int,
            result=ExactOriginRC(int),
        ),
        param_result(
            List,
            result=ExactOriginRC(list),
        ),
        param_result(
            dict,
            result=ExactOriginRC(dict),
        ),
        param_result(
            Iterable,
            result=OriginSubclassRC(collections.abc.Iterable),
        ),
        param_result(
            Iterable[int],
            result=ExactTypeRC(normalize_type(Iterable[int])),
        ),
        param_result(
            List[int],
            result=ExactTypeRC(normalize_type(List[int])),
        ),
        param_result(
            List[T],
            raises=ValueError,
            exact_match='Can not create RequestChecker from typing.List[~T] generic alias (parametrized generic)',
        ),
        param_result(
            Union,
            result=ExactOriginRC(Union)
        ),
        *cond_list(
            HAS_ANNOTATED,
            lambda: [
                param_result(
                    typing.Annotated,
                    result=ExactOriginRC(typing.Annotated)
                ),
                param_result(
                    typing.Annotated[int, 'meta'],
                    result=ExactTypeRC(normalize_type(typing.Annotated[int, 'meta']))
                ),
                param_result(
                    typing.Annotated[List[int], 'meta'],
                    result=ExactTypeRC(normalize_type(typing.Annotated[list[int], 'meta']))
                ),
                param_result(
                    typing.Annotated[list, 'meta'],
                    raises=ValueError,
                    exact_match=(
                        "Can not create RequestChecker from"
                        " typing.Annotated[list, 'meta'] generic alias (parametrized generic)"
                    ),
                ),
                param_result(
                    typing.Annotated[List[T], 'meta'],
                    raises=ValueError,
                    exact_match=(
                        "Can not create RequestChecker from"
                        " typing.Annotated[typing.List[~T], 'meta'] generic alias (parametrized generic)"
                    ),
                ),
                param_result(
                    typing.Annotated[Dict[int, T], 'meta'],
                    raises=ValueError,
                    exact_match=(
                        "Can not create RequestChecker from"
                        " typing.Annotated[typing.Dict[int, ~T], 'meta'] generic alias (parametrized generic)"
                    ),
                ),
            ]
        ),
    ],
)
def test_create_request_checker(value, result, context):
    with context or nullcontext():
        assert create_request_checker(value) == result
