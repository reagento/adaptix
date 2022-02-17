from typing import Set, Tuple

import pytest

from dataclass_factory_30.provider import (
    NameMapper, NameStyle,
    ValueProvider, CfgExtraPolicy,
    ExtraSkip, InputNameMappingRequest,
    InputFieldsFigure, NoDefault,
)
from dataclass_factory_30.provider.fields_basics import (
    NameMapping, DictCrown, FieldCrown,
    ExtraTargets, FigureExtra,
    OutputNameMappingRequest, OutputFieldsFigure,
    GetterKind
)
from dataclass_factory_30.provider.request_cls import InputFieldRM, ParamKind, FieldRM
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


def make_field(name: str, is_required: bool):
    return InputFieldRM(
        name=name,
        type=int,
        default=NoDefault(),
        is_required=is_required,
        metadata={},
        param_kind=ParamKind.POS_OR_KW,
    )


def inp_request(fields: Tuple[InputFieldRM, ...], extra: FigureExtra = None):
    return InputNameMappingRequest(
        type=Stub,
        figure=InputFieldsFigure(
            constructor=Stub,
            extra=extra,
            fields=fields
        ),
    )


def out_request(fields: Tuple[FieldRM, ...]):
    return OutputNameMappingRequest(
        type=Stub,
        figure=OutputFieldsFigure(
            fields=fields,
            getter_kind=GetterKind.ATTR,
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


@pytest.fixture(params=[inp_request, out_request])
def make_request(request):
    return request.param


def test_name_mapping_simple(factory, make_request):
    name_mapping = factory.provide(
        make_request(
            fields=(
                make_field(
                    name="a",
                    is_required=True,
                ),
                make_field(
                    name="b",
                    is_required=True,
                ),
            )
        )
    )

    assert name_mapping == NameMapping(
        crown=DictCrown(
            {
                'a': FieldCrown('a'),
                'b': FieldCrown('b'),
            },
            extra=ExtraSkip(),
        ),
        skipped_extra_targets=[],
    )


def test_name_mapping_skipping(factory, make_request):
    name_mapping = factory.provide(
        make_request(
            fields=(
                make_field(
                    name="a",
                    is_required=True,
                ),
                make_field(
                    name="c",
                    is_required=False,
                ),
            )
        )
    )

    assert name_mapping == NameMapping(
        crown=DictCrown(
            {
                'a': FieldCrown('a'),
            },
            extra=ExtraSkip(),
        ),
        skipped_extra_targets=[],
    )


def test_name_mapping_extra_targets(factory):
    name_mapping = factory.provide(
        inp_request(
            fields=(
                make_field(
                    name="a",
                    is_required=True,
                ),
                make_field(
                    name="b",
                    is_required=False,
                ),
            ),
            extra=ExtraTargets(('b',))
        )
    )

    assert name_mapping == NameMapping(
        crown=DictCrown(
            {
                'a': FieldCrown('a'),
            },
            extra=ExtraSkip(),
        ),
        skipped_extra_targets=[],
    )


def test_name_mapping_extra_targets_skip(factory):
    name_mapping = factory.provide(
        inp_request(
            fields=(
                make_field(
                    name="a",
                    is_required=True,
                ),
                make_field(
                    name="c",
                    is_required=False,
                ),
            ),
            extra=ExtraTargets(('c',))
        )
    )

    assert name_mapping == NameMapping(
        crown=DictCrown(
            {
                'a': FieldCrown('a'),
            },
            extra=ExtraSkip(),
        ),
        skipped_extra_targets=['c'],
    )


def test_name_mapping_error_on_required_field_skip(factory):
    with pytest.raises(ValueError):
        factory.provide(
            inp_request(
                fields=(
                    make_field(
                        name="a",
                        is_required=True,
                    ),
                    make_field(
                        name="c",
                        is_required=True,
                    ),
                ),
                extra=None,
            )
        )

    with pytest.raises(ValueError):
        factory.provide(
            inp_request(
                fields=(
                    make_field(
                        name="a",
                        is_required=True,
                    ),
                    make_field(
                        name="c",
                        is_required=True,
                    ),
                ),
                extra=ExtraTargets(("c",))
            )
        )
