import re
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Callable, Dict, Optional

import pytest

from dataclass_factory_30.common import Parser, VarTuple
from dataclass_factory_30.facade import bound
from dataclass_factory_30.model_tools import (
    ExtraKwargs,
    ExtraSaturate,
    ExtraTargets,
    InpFigureExtra,
    InputField,
    InputFigure,
    NoDefault,
    ParamKind,
)
from dataclass_factory_30.provider import (
    BuiltinInputExtractionMaker,
    ExtraFieldsError,
    ExtraItemsError,
    InputFigureRequest,
    InputNameMappingRequest,
    ModelParserProvider,
    NameSanitizer,
    NoRequiredFieldsError,
    NoRequiredItemsError,
    ParseError,
    ParserRequest,
    TypeParseError,
    ValueProvider,
    make_input_creation,
)
from dataclass_factory_30.provider.model import (
    ExtraCollect,
    ExtraForbid,
    ExtraSkip,
    InpDictCrown,
    InpFieldCrown,
    InpListCrown,
    InpNoneCrown,
    InputNameMapping,
)
from tests_helpers import DebugCtx, TestFactory, parametrize_bool, raises_path


@dataclass
class Gauge:
    args: VarTuple[Any]
    kwargs: Dict[str, Any]
    extra: Optional[dict] = None

    def with_extra(self, new_extra: Optional[dict]):
        return replace(self, extra=new_extra)

    @classmethod
    def saturate(cls, obj, extra) -> None:
        obj.extra = extra


def gauge(*args, **kwargs):
    return Gauge(args, kwargs)


def field(name: str, param_kind: ParamKind, is_required: bool):
    return InputField(
        type=int,
        name=name,
        default=NoDefault(),
        is_required=is_required,
        metadata=MappingProxyType({}),
        param_kind=param_kind,
        param_name=name,
    )


def figure(*fields: InputField, extra: InpFigureExtra):
    return InputFigure(
        fields=fields,
        constructor=gauge,
        extra=extra,
    )


def int_parser(data):
    if isinstance(data, BaseException):
        raise data
    return data


def make_parser_getter(
    fig: InputFigure,
    name_mapping: InputNameMapping,
    debug_path: bool,
    debug_ctx: DebugCtx,
) -> Callable[[], Parser]:
    def getter():
        factory = TestFactory(
            recipe=[
                ValueProvider(InputFigureRequest, fig),
                ValueProvider(InputNameMappingRequest, name_mapping),
                bound(int, ValueProvider(ParserRequest, int_parser)),
                ModelParserProvider(NameSanitizer(), BuiltinInputExtractionMaker(), make_input_creation),
                debug_ctx.accum,
            ]
        )

        parser = factory.provide(
            ParserRequest(type=Gauge, debug_path=debug_path, strict_coercion=False)
        )
        return parser

    return getter


@pytest.fixture(params=[ExtraSkip(), ExtraForbid(), ExtraCollect()])
def extra_policy(request):
    return request.param


def test_direct(debug_ctx, debug_path, extra_policy):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
            extra=None
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                    'b': InpFieldCrown('b'),
                },
                extra=extra_policy,
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )

    if extra_policy == ExtraCollect():
        pytest.raises(ValueError, parser_getter).match(
            "Cannot create parser that collect extra data if InputFigure does not take extra data"
        )
        return

    parser = parser_getter()
    assert parser({'a': 1, 'b': 2}) == gauge(1, 2)

    if extra_policy == ExtraSkip():
        assert parser({'a': 1, 'b': 2, 'c': 3}) == gauge(1, 2)
    if extra_policy == ExtraForbid():
        raises_path(
            ExtraFieldsError({'c'}),
            lambda: parser({'a': 1, 'b': 2, 'c': 3}),
            path=[],
        )

    raises_path(
        ParseError(),
        lambda: parser({'a': 1, 'b': ParseError()}),
        path=['b'] if debug_path else [],
    )

    raises_path(
        NoRequiredFieldsError(['b']),
        lambda: parser({'a': 1}),
        path=[],
    )

    raises_path(
        TypeParseError(dict),
        lambda: parser("bad input value"),
        path=[],
    )


@pytest.mark.parametrize('extra_policy', [ExtraSkip(), ExtraForbid()])
def test_direct_list(debug_ctx, debug_path, extra_policy):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
            extra=None
        ),
        name_mapping=InputNameMapping(
            crown=InpListCrown(
                [
                    InpFieldCrown('a'),
                    InpFieldCrown('b'),
                ],
                extra=extra_policy,
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )

    parser = parser_getter()
    assert parser([1, 2]) == gauge(1, 2)

    if extra_policy == ExtraSkip():
        assert parser([1, 2, 3]) == gauge(1, 2)

    if extra_policy == ExtraForbid():
        raises_path(
            ExtraItemsError(2),
            lambda: parser([1, 2, 3]),
            path=[],
        )

    raises_path(
        NoRequiredItemsError(2),
        lambda: parser([10]),
        path=[],
    )

    raises_path(
        TypeParseError(list),
        lambda: parser("bad input value"),
        path=[],
    )


def test_extra_forbid(debug_ctx, debug_path):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
            extra=None
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                    'b': InpFieldCrown('b'),
                },
                extra=ExtraForbid(),
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )

    parser = parser_getter()

    raises_path(
        ExtraFieldsError({'c'}),
        lambda: parser({'a': 1, 'b': 2, 'c': 3}),
        path=[],
    )
    raises_path(
        ExtraFieldsError({'c', 'd'}),
        lambda: parser({'a': 1, 'b': 2, 'c': 3, 'd': 4}),
        path=[],
    )


def test_creation(debug_ctx, debug_path, extra_policy):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_ONLY, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
            field('c', ParamKind.POS_OR_KW, is_required=False),
            field('d', ParamKind.KW_ONLY, is_required=True),
            field('e', ParamKind.KW_ONLY, is_required=False),
            extra=ExtraKwargs()
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                    'b': InpFieldCrown('b'),
                    'c': InpFieldCrown('c'),
                    'd': InpFieldCrown('d'),
                    'e': InpFieldCrown('e'),
                },
                extra=extra_policy,
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    parser = parser_getter()

    assert parser({'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5}) == gauge(1, 2, c=3, d=4, e=5)


def test_extra_kwargs(debug_ctx, debug_path):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_ONLY, is_required=True),
            extra=ExtraKwargs()
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                },
                extra=ExtraCollect(),
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    parser = parser_getter()

    assert parser({'a': 1}) == gauge(1)
    assert parser({'a': 1, 'b': 2}) == gauge(1, b=2)


@parametrize_bool('is_required')
def test_extra_targets_one(debug_ctx, debug_path, is_required):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=is_required),
            extra=ExtraTargets(('b',))
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                },
                extra=ExtraCollect(),
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    parser = parser_getter()

    assert parser({'a': 1}) == gauge(1, {})
    assert parser({'a': 1, 'c': 2}) == gauge(1, {'c': 2})
    assert parser({'a': 1, 'b': 2}) == gauge(1, {'b': 2})
    assert parser({'a': 1, 'b': 2, 'c': 3}) == gauge(1, {'b': 2, 'c': 3})


@parametrize_bool('is_required_first', 'is_required_second')
def test_extra_targets_two(debug_ctx, debug_path, is_required_first, is_required_second):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=is_required_first),
            field('c', ParamKind.KW_ONLY, is_required=is_required_second),
            extra=ExtraTargets(('b', 'c'))
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                },
                extra=ExtraCollect(),
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    parser = parser_getter()

    assert parser({'a': 1}) == gauge(1, {}, c={})
    assert parser({'a': 1, 'd': 2}) == gauge(1, {'d': 2}, c={'d': 2})
    assert parser({'a': 1, 'b': 2}) == gauge(1, {'b': 2}, c={'b': 2})
    assert parser({'a': 1, 'c': 2}) == gauge(1, {'c': 2}, c={'c': 2})
    assert parser({'a': 1, 'b': 2, 'c': 3}) == gauge(1, {'b': 2, 'c': 3}, c={'b': 2, 'c': 3})
    assert parser({'a': 1, 'b': 2, 'c': 3, 'd': 4}) == gauge(1, {'b': 2, 'c': 3, 'd': 4}, c={'b': 2, 'c': 3, 'd': 4})


def test_extra_saturate(debug_ctx, debug_path):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_ONLY, is_required=True),
            extra=ExtraSaturate(Gauge.saturate)
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                },
                extra=ExtraCollect(),
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    parser = parser_getter()

    assert parser({'a': 1}) == gauge(1).with_extra({})
    assert parser({'a': 1, 'b': 2}) == gauge(1).with_extra({'b': 2})


def test_mapping_and_extra_kwargs(debug_ctx, debug_path):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=False),
            extra=ExtraKwargs(),
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                    'm_b': InpFieldCrown('b'),
                },
                extra=ExtraCollect(),
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    parser = parser_getter()

    raises_path(
        NoRequiredFieldsError(['m_a']),
        lambda: parser({'a': 1, 'b': 2}),
        path=[],
    )

    assert parser({'m_a': 1, 'b': 'this value is not parsed'}) == gauge(1, b='this value is not parsed')
    assert parser({'m_a': 1, 'm_b': 2}) == gauge(1, b=2)
    pytest.raises(
        TypeError, lambda: parser({'m_a': 1, 'm_b': 2, 'b': 3}),
    ).match("got multiple values for keyword argument 'b'")


def test_skipped_required_field(debug_ctx, debug_path, extra_policy):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
            extra=None,
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                },
                extra=extra_policy,
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, parser_getter).match(re.escape("Required fields ['b'] are skipped"))

    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
            extra=ExtraTargets(('b',)),
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                },
                extra=extra_policy,
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    parser_getter()

    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
            extra=ExtraTargets(('b',)),
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                },
                extra=extra_policy,
            ),
            skipped_extra_targets=['b'],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, parser_getter).match(re.escape("Required fields ['b'] are skipped"))


def test_extra_target_at_crown(debug_ctx, debug_path, extra_policy):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
            extra=ExtraTargets(('b',)),
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                    'm_b': InpFieldCrown('b'),
                },
                extra=extra_policy,
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, parser_getter).match(
        re.escape("Extra targets ['b'] are found at crown")
    )

    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=False),
            extra=ExtraTargets(('b',)),
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                    'm_b': InpFieldCrown('b'),
                },
                extra=extra_policy,
            ),
            skipped_extra_targets=['b'],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, parser_getter).match(
        re.escape("Extra targets ['b'] are found at crown")
    )


def test_optional_fields_at_list(debug_ctx, debug_path, extra_policy):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=False),
            extra=None,
        ),
        name_mapping=InputNameMapping(
            crown=InpListCrown(
                [
                    InpFieldCrown('a'),
                    InpFieldCrown('b'),
                ],
                extra=extra_policy,
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, parser_getter).match(
        re.escape("Optional fields ['b'] are found at list crown")
    )


@parametrize_bool('is_required')
def test_flat_mapping(debug_ctx, debug_path, is_required):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=False),
            field('e', ParamKind.KW_ONLY, is_required=is_required),
            extra=ExtraTargets(('e',)),
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                    'm_b': InpFieldCrown('b'),
                },
                extra=ExtraCollect(),
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    parser = parser_getter()

    raises_path(
        NoRequiredFieldsError(['m_a']),
        lambda: parser({'a': 1, 'b': 2}),
        path=[],
    )

    assert parser({'m_a': 1, 'b': 2}) == gauge(1, e={'b': 2})
    assert parser({'m_a': 1, 'm_b': 2}) == gauge(1, b=2, e={})
    assert parser({'m_a': 1, 'm_b': 2, 'b': 3}) == gauge(1, b=2, e={'b': 3})


COMPLEX_STRUCTURE_FIGURE = figure(
    field('a', ParamKind.KW_ONLY, is_required=True),
    field('b', ParamKind.KW_ONLY, is_required=True),
    field('c', ParamKind.KW_ONLY, is_required=True),
    field('d', ParamKind.KW_ONLY, is_required=True),
    field('e', ParamKind.KW_ONLY, is_required=True),
    field('f', ParamKind.KW_ONLY, is_required=True),
    field('extra', ParamKind.KW_ONLY, is_required=True),
    extra=ExtraTargets(('extra',)),
)

COMPLEX_STRUCTURE_CROWN = InpDictCrown(
    {
        'z': InpDictCrown(
            {
                'y': InpFieldCrown('a'),
                'x': InpFieldCrown('b'),
            },
            extra=ExtraCollect(),
        ),
        'w': InpFieldCrown('c'),
        'v': InpListCrown(
            [
                InpFieldCrown('d'),
                InpDictCrown(
                    {
                        'u': InpFieldCrown('e'),
                    },
                    extra=ExtraCollect(),
                ),
                InpListCrown(
                    [
                        InpFieldCrown('f')
                    ],
                    extra=ExtraForbid(),
                )
            ],
            extra=ExtraForbid(),
        ),
    },
    extra=ExtraCollect(),
)


def test_structure_flattening(debug_ctx, debug_path):
    parser_getter = make_parser_getter(
        fig=COMPLEX_STRUCTURE_FIGURE,
        name_mapping=InputNameMapping(
            crown=COMPLEX_STRUCTURE_CROWN,
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    parser = parser_getter()

    assert parser(
        {
            'z': {
                'y': 1,
                'x': 2,
            },
            'w': 3,
            'v': [
                4,
                {'u': 5},
                [6],
            ],
        }
    ) == gauge(
        a=1, b=2, c=3, d=4, e=5, f=6,
        extra={
            'z': {},
            'v': [{}, {}, [{}]],
        }
    )

    assert parser(
        {
            'z': {
                'y': 1,
                'x': 2,
                'extra_1': 3,
            },
            'w': 4,
            'v': [
                5,
                {'u': 6, 'extra_2': 7},
                [8],
            ],
            'extra_3': 9,
        }
    ) == gauge(
        a=1, b=2, c=4, d=5, e=6, f=8,
        extra={
            'z': {'extra_1': 3},
            'v': [{}, {'extra_2': 7}, [{}]],
            'extra_3': 9,
        }
    )

    raises_path(
        TypeParseError(dict),
        lambda: parser(
            {
                'z': 'this is not a dict',
                'w': 3,
                'v': [
                    4,
                    {'u': 5},
                    [6],
                ],
            }
        ),
        path=['z'] if debug_path else []
    )

    raises_path(
        TypeParseError(list),
        lambda: parser(
            {
                'z': {
                    'y': 1,
                    'x': 2,
                },
                'w': 3,
                'v': 'this is not a list',
            }
        ),
        path=['v'] if debug_path else []
    )


def _replace_value_by_path(data, path, new_value):
    sub_data = data

    for idx, path_element in enumerate(path):
        if idx + 1 == len(path):
            sub_data[path_element] = new_value
            return

        sub_data = sub_data[path_element]


@pytest.mark.parametrize(
    'error_path',
    [
        ['z', 'y'],
        ['w'],
        ['v', 0],
        ['v', 1, 'u'],
        ['v', 2, 0]
    ],
)
def test_error_path_at_complex_structure(debug_ctx, debug_path, error_path):
    parser_getter = make_parser_getter(
        fig=COMPLEX_STRUCTURE_FIGURE,
        name_mapping=InputNameMapping(
            crown=COMPLEX_STRUCTURE_CROWN,
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    parser = parser_getter()

    data = {
        'z': {
            'y': 1,
            'x': 2,
        },
        'w': 3,
        'v': [
            4,
            {'u': 5},
            [6],
        ],
    }

    _replace_value_by_path(data, error_path, ParseError())

    raises_path(
        ParseError(),
        lambda: parser(data),
        path=error_path if debug_path else []
    )


def test_none_crown_at_dict_crown(debug_ctx, debug_path, extra_policy):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('extra', ParamKind.KW_ONLY, is_required=True),
            extra=ExtraTargets(('extra',)),
        ),
        name_mapping=InputNameMapping(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                    'b': InpNoneCrown(),
                },
                extra=extra_policy,
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    parser = parser_getter()

    assert parser({'a': 1}) == gauge(1, extra={})
    assert parser({'a': 1, 'b': 2}) == gauge(1, extra={})

    if extra_policy == ExtraSkip():
        assert parser({'a': 1, 'b': 2, 'c': 3}) == gauge(1, extra={})

    if extra_policy == ExtraCollect():
        assert parser({'a': 1, 'b': 2, 'c': 3}) == gauge(1, extra={'c': 3})

    if extra_policy == ExtraForbid():
        raises_path(
            ExtraFieldsError({'c'}),
            lambda: parser({'a': 1, 'b': 2, 'c': 3}),
            path=[],
        )


@pytest.mark.parametrize('extra_policy', [ExtraSkip(), ExtraForbid()])
def test_none_crown_at_list_crown(debug_ctx, debug_path, extra_policy):
    parser_getter = make_parser_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            extra=None,
        ),
        name_mapping=InputNameMapping(
            crown=InpListCrown(
                [
                    InpNoneCrown(),
                    InpFieldCrown('a'),
                    InpNoneCrown(),
                ],
                extra=extra_policy,
            ),
            skipped_extra_targets=[],
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    parser = parser_getter()

    assert parser([1, 2, 3]) == gauge(2)

    raises_path(
        NoRequiredItemsError(3),
        lambda: parser([1, 2]),
        path=[],
    )

    if extra_policy == ExtraSkip():
        assert parser([1, 2, 3, 4]) == gauge(2)

    if extra_policy == ExtraForbid():
        raises_path(
            ExtraItemsError(3),
            lambda: parser([1, 2, 3, 4]),
            path=[],
        )
