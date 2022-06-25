from dataclasses import dataclass
from typing import Set, List, Iterable

import pytest

from dataclass_factory_30.provider import (
    NameMapper, NameStyle,
    ValueProvider,
    ExtraSkip, InputNameMappingRequest,
    InputFigure, NoDefault, OutputFigure, ExtraTargets,
)
from dataclass_factory_30.provider.definitions import AttrAccessor
from dataclass_factory_30.provider.fields import OutFigureExtra, InpFigureExtra
from dataclass_factory_30.provider.fields.crown_definitions import (
    CfgExtraPolicy, OutputNameMappingRequest, InpDictCrown,
    InpFieldCrown, InputNameMapping, OutputNameMapping, OutDictCrown, OutFieldCrown,
)
from dataclass_factory_30.provider.request_cls import ParamKind, InputFieldRM, OutputFieldRM
from tests_30.provider.conftest import TestFactory


def check_name_mapper(mapper: NameMapper, source: Set[str], target: Set[str]):
    result = set()
    for s_name in source:
        if not mapper._should_skip(s_name):
            result.add(mapper._convert_name(s_name))

    assert result == target


def test_default():
    check_name_mapper(
        NameMapper(),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a', 'b', 'd'},
    )


def test_name_mutating():
    check_name_mapper(
        NameMapper(
            map={},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'A', 'B', 'D'},
    )
    check_name_mapper(
        NameMapper(
            map={'a': 'z'},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z', 'B', 'D'},
    )
    check_name_mapper(
        NameMapper(
            map={'a': 'z'},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z', 'B', 'D'},
    )
    check_name_mapper(
        NameMapper(
            map={'a': 'z', '_c': 'x'},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z', 'B', 'D'},
    )
    check_name_mapper(
        NameMapper(
            map={'a': 'z', 'd_': 'w'},
            name_style=NameStyle.UPPER,
            trim_trailing_underscore=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'z', 'B', 'w'},
    )
    check_name_mapper(
        NameMapper(
            map={'a': '_z'},
            name_style=NameStyle.UPPER,
            trim_trailing_underscore=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'_z', 'B', 'D'},
    )
    check_name_mapper(
        NameMapper(
            map={},
            trim_trailing_underscore=False,
            name_style=NameStyle.UPPER,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'A', 'B', 'D_'},
    )


def test_name_filtering():
    check_name_mapper(
        NameMapper(
            skip=['a', 'xxx'],
            only_mapped=False,
            only=None,
            skip_internal=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'b', 'd'},
    )
    check_name_mapper(
        NameMapper(
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
        NameMapper(
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
        NameMapper(
            skip=[],
            only_mapped=False,
            only=['a', '_c'],
            skip_internal=True,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a', '_c'},
    )
    check_name_mapper(
        NameMapper(
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
        NameMapper(
            skip=['b'],
            only_mapped=False,
            only=['a', 'b'],
            skip_internal=False,
        ),
        {'a', 'b', '_c', 'd_', '_e_'},
        {'a'},
    )
    check_name_mapper(
        NameMapper(
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
        NameMapper(
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


def inp_request(fields: List[MapField], extra: InpFigureExtra = None):
    return InputNameMappingRequest(
        type=Stub,
        figure=InputFigure(
            constructor=Stub,
            extra=extra,
            fields=tuple(
                InputFieldRM(
                    type=int,
                    name=field.name,
                    default=NoDefault(),
                    is_required=field.is_required,
                    metadata={},
                    param_kind=ParamKind.POS_OR_KW,
                )
                for field in fields
            ),
        ),
    )


def out_request(fields: Iterable[MapField], extra: OutFigureExtra = None):
    return OutputNameMappingRequest(
        type=Stub,
        figure=OutputFigure(
            extra=extra,
            fields=tuple(
                OutputFieldRM(
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
def factory():
    return TestFactory(
        [
            NameMapper(skip=['c'], map={'d': 'z'}),
            ValueProvider(CfgExtraPolicy, ExtraSkip()),
        ]
    )


def test_name_mapping_simple(factory):
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

    inp_name_mapping = factory.provide(
        inp_request(fields=fields)
    )

    assert inp_name_mapping == InputNameMapping(
        crown=InpDictCrown(
            {
                'a': InpFieldCrown('a'),
                'b': InpFieldCrown('b'),
            },
            extra=ExtraSkip(),
        ),
        skipped_extra_targets=[],
    )

    out_name_mapping = factory.provide(
        out_request(fields=fields)
    )

    assert out_name_mapping == OutputNameMapping(
        crown=OutDictCrown(
            {
                'a': OutFieldCrown('a'),
                'b': OutFieldCrown('b'),
            },
            sieves={},
        ),
        skipped_extra_targets=[],
    )


def test_name_mapping_skipping(factory):
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

    inp_name_mapping = factory.provide(
        inp_request(fields)
    )

    assert inp_name_mapping == InputNameMapping(
        crown=InpDictCrown(
            {
                'a': InpFieldCrown('a'),
            },
            extra=ExtraSkip(),
        ),
        skipped_extra_targets=[],
    )

    out_name_mapping = factory.provide(
        out_request(fields)
    )

    assert out_name_mapping == OutputNameMapping(
        crown=OutDictCrown(
            {
                'a': OutFieldCrown('a'),
            },
            sieves={},
        ),
        skipped_extra_targets=[],
    )


def test_name_mapping_extra_targets(factory):
    fields = [
        MapField(
            name="a",
            is_required=True,
        ),
        MapField(
            name="b",
            is_required=False,
        ),
    ]

    inp_name_mapping = factory.provide(
        inp_request(fields, extra=ExtraTargets(('b',)))
    )

    assert inp_name_mapping == InputNameMapping(
        crown=InpDictCrown(
            {
                'a': InpFieldCrown('a'),
            },
            extra=ExtraSkip(),
        ),
        skipped_extra_targets=[],
    )

    out_name_mapping = factory.provide(
        out_request(fields, extra=ExtraTargets(('b',)))
    )

    assert out_name_mapping == OutputNameMapping(
        crown=OutDictCrown(
            {
                'a': OutFieldCrown('a'),
            },
            sieves={},
        ),
        skipped_extra_targets=[],
    )


def test_name_mapping_extra_targets_skip(factory):
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

    inp_name_mapping = factory.provide(
        inp_request(fields, extra=ExtraTargets(('c',)))
    )

    assert inp_name_mapping == InputNameMapping(
        crown=InpDictCrown(
            {
                'a': InpFieldCrown('a'),
            },
            extra=ExtraSkip(),
        ),
        skipped_extra_targets=['c'],
    )

    out_name_mapping = factory.provide(
        out_request(fields, extra=ExtraTargets(('c',)))
    )

    assert out_name_mapping == OutputNameMapping(
        crown=OutDictCrown(
            {
                'a': OutFieldCrown('a'),
            },
            sieves={},
        ),
        skipped_extra_targets=['c'],
    )


def test_name_mapping_error_on_required_field_skip(factory):
    with pytest.raises(ValueError):
        factory.provide(
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
                extra=None,
            )
        )

    with pytest.raises(ValueError):
        factory.provide(
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
                extra=ExtraTargets(("c",))
            )
        )
