import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Set

import pytest

from dataclass_factory_30.model_tools import (
    AttrAccessor,
    InputField,
    InputFigure,
    NoDefault,
    OutputField,
    OutputFigure,
    ParamKind,
    ParamKwargs,
)
from dataclass_factory_30.provider import InputNameLayoutRequest, NameStyle, NameToPathMaker, ValueProvider
from dataclass_factory_30.provider.model.crown_definitions import (
    ExtraSkip,
    InpDictCrown,
    InpFieldCrown,
    InputNameLayout,
    OutDictCrown,
    OutFieldCrown,
    OutputNameLayout,
    OutputNameLayoutRequest,
)
from tests_helpers import TestRetort


def check_name_mapper(mapper: NameToPathMaker, source: Set[str], target: Set[str]):
    result = set()
    for s_name in source:
        if not mapper._should_skip(s_name):
            result.add(mapper._convert_name(s_name))

    assert result == target


def test_default():
    check_name_mapper(
        NameToPathMaker(),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a', 'b', 'd'},
    )


def test_name_mutating():
    check_name_mapper(
        NameToPathMaker(
            map={},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'A', 'B', 'D'},
    )
    check_name_mapper(
        NameToPathMaker(
            map={'a': 'z'},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z', 'B', 'D'},
    )
    check_name_mapper(
        NameToPathMaker(
            map={'a': 'z'},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z', 'B', 'D'},
    )
    check_name_mapper(
        NameToPathMaker(
            map={'a': 'z', '_c': 'x'},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z', 'B', 'D'},
    )
    check_name_mapper(
        NameToPathMaker(
            map={'a': 'z', 'd_': 'w'},
            name_style=NameStyle.UPPER,
            trim_trailing_underscore=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z', 'B', 'w'},
    )
    check_name_mapper(
        NameToPathMaker(
            map={'a': '_z'},
            name_style=NameStyle.UPPER,
            trim_trailing_underscore=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'_z', 'B', 'D'},
    )
    check_name_mapper(
        NameToPathMaker(
            map={},
            trim_trailing_underscore=False,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'A', 'B', 'D_'},
    )


def test_name_filtering():
    check_name_mapper(
        NameToPathMaker(
            skip=['a', 'xxx'],
            only_mapped=False,
            only=None,
            skip_internal=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'b', 'd'},
    )
    check_name_mapper(
        NameToPathMaker(
            skip=[],
            only_mapped=True,
            only=None,
            skip_internal=True,
            map={},
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        set(),
    )
    check_name_mapper(
        NameToPathMaker(
            skip=[],
            only_mapped=True,
            only=None,
            skip_internal=True,
            map={'a': 'z'},
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z'},
    )
    check_name_mapper(
        NameToPathMaker(
            skip=[],
            only_mapped=False,
            only=['a', '_c'],
            skip_internal=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a', '_c'},
    )
    check_name_mapper(
        NameToPathMaker(
            skip=[],
            only_mapped=True,
            only=['a'],
            skip_internal=False,
            map={'b': 'y'}
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a', 'y'},
    )
    check_name_mapper(
        NameToPathMaker(
            skip=['b'],
            only_mapped=False,
            only=['a', 'b'],
            skip_internal=False,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a'},
    )
    check_name_mapper(
        NameToPathMaker(
            skip=['b'],
            only_mapped=True,
            only=None,
            skip_internal=True,
            map={'a': 'z', 'b': 'y'}
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z'},
    )
    check_name_mapper(
        NameToPathMaker(
            skip=[],
            only_mapped=False,
            only=['a', '_c'],
            skip_internal=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a', '_c'},
    )


class Stub:
    def __init__(self, *args):
        pass


@dataclass
class MapField:
    name: str
    is_required: bool


def inp_request(fields: List[MapField], kwargs: Optional[ParamKwargs] = None):
    return InputNameLayoutRequest(
        type=Stub,
        figure=InputFigure(
            constructor=Stub,
            kwargs=kwargs,
            fields=tuple(
                InputField(
                    type=int,
                    name=field.name,
                    default=NoDefault(),
                    is_required=field.is_required,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                    param_name=field.name,
                )
                for field in fields
            ),
        ),
    )


def out_request(fields: Iterable[MapField]):
    return OutputNameLayoutRequest(
        type=Stub,
        figure=OutputFigure(
            fields=tuple(
                OutputField(
                    type=int,
                    name=field.name,
                    default=NoDefault(),
                    metadata={},
                    accessor=AttrAccessor(
                        field.name,
                        is_required=field.is_required,
                    ),
                )
                for field in fields
            ),
        ),
    )


@pytest.fixture
def retort():
    return TestRetort(
        [
            NameToPathMaker(
                skip=['c'],
                map={'d': 'z'},
                extra_in=ExtraSkip(),
            ),
        ]
    )


def test_name_mapping_simple(retort):
    fields = [
        MapField(
            name="a",
            is_required=True,
        ),
        MapField(
            name="b",
            is_required=True,
        ),
    ]

    inp_name_mapping = retort.provide(
        inp_request(fields=fields)
    )

    assert inp_name_mapping == InputNameLayout(
        crown=InpDictCrown(
            {
                'a': InpFieldCrown('a'),
                'b': InpFieldCrown('b'),
            },
            extra_policy=ExtraSkip(),
        ),
        extra_move=None,
    )

    out_name_mapping = retort.provide(
        out_request(fields=fields)
    )

    assert out_name_mapping == OutputNameLayout(
        crown=OutDictCrown(
            {
                'a': OutFieldCrown('a'),
                'b': OutFieldCrown('b'),
            },
            sieves={},
        ),
        extra_move=None,
    )


def test_name_mapping_skipping(retort):
    fields = [
        MapField(
            name="a",
            is_required=True,
        ),
        MapField(
            name="c",
            is_required=False,
        ),
    ]

    inp_name_mapping = retort.provide(
        inp_request(fields)
    )

    assert inp_name_mapping == InputNameLayout(
        crown=InpDictCrown(
            {
                'a': InpFieldCrown('a'),
            },
            extra_policy=ExtraSkip(),
        ),
        extra_move=None,
    )

    out_name_mapping = retort.provide(
        out_request(fields)
    )

    assert out_name_mapping == OutputNameLayout(
        crown=OutDictCrown(
            {
                'a': OutFieldCrown('a'),
            },
            sieves={},
        ),
        extra_move=None,
    )


def test_name_mapping_error_on_required_field_skip(retort):
    string_to_match = re.escape(
        "Can not create name mapping for type <class 'tests_30.provider.test_name_mapper.Stub'>"
        " that skips required fields ['c']"
    )

    with pytest.raises(ValueError, match=string_to_match):
        retort.provide(
            inp_request(
                fields=[
                    MapField(
                        name="a",
                        is_required=True,
                    ),
                    MapField(
                        name="c",
                        is_required=True,
                    ),
                ],
            )
        )
