from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Callable, Dict, Optional

import pytest

from adaptix import ExtraKwargs, Loader, bound
from adaptix._internal.common import VarTuple
from adaptix._internal.model_tools import InputField, InputFigure, NoDefault, ParamKind, ParamKwargs
from adaptix._internal.provider import (
    BuiltinInputExtractionMaker,
    ExtraFieldsError,
    ExtraItemsError,
    InputFigureRequest,
    InputNameLayoutRequest,
    LoaderRequest,
    LoadError,
    ModelLoaderProvider,
    NameSanitizer,
    NoRequiredFieldsError,
    NoRequiredItemsError,
    TypeLoadError,
    ValueProvider,
    make_input_creation,
)
from adaptix._internal.provider.model import (
    ExtraCollect,
    ExtraForbid,
    ExtraSkip,
    InpDictCrown,
    InpFieldCrown,
    InpListCrown,
    InpNoneCrown,
    InputNameLayout,
)
from adaptix._internal.provider.model.crown_definitions import ExtraSaturate, ExtraTargets
from tests_helpers import DebugCtx, TestRetort, full_match_regex_str, parametrize_bool, raises_path


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
        id=name,
        default=NoDefault(),
        is_required=is_required,
        metadata=MappingProxyType({}),
        param_kind=param_kind,
        param_name=name,
    )


def figure(*fields: InputField, kwargs: Optional[ParamKwargs] = None):
    return InputFigure(
        fields=fields,
        constructor=gauge,
        kwargs=kwargs,
        overriden_types=frozenset(fld.id for fld in fields),
    )


def int_loader(data):
    if isinstance(data, BaseException):
        raise data
    return data


def make_loader_getter(
    fig: InputFigure,
    name_layout: InputNameLayout,
    debug_path: bool,
    debug_ctx: DebugCtx,
) -> Callable[[], Loader]:
    def getter():
        retort = TestRetort(
            recipe=[
                ValueProvider(InputFigureRequest, fig),
                ValueProvider(InputNameLayoutRequest, name_layout),
                bound(int, ValueProvider(LoaderRequest, int_loader)),
                ModelLoaderProvider(NameSanitizer(), BuiltinInputExtractionMaker(), make_input_creation),
                debug_ctx.accum,
            ]
        )

        loader = retort.replace(
            debug_path=debug_path,
            strict_coercion=False,
        ).get_loader(
            Gauge,
        )
        return loader

    return getter


@pytest.fixture(params=[ExtraSkip(), ExtraForbid(), ExtraCollect()])
def extra_policy(request):
    return request.param


def test_direct(debug_ctx, debug_path, extra_policy):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                    'b': InpFieldCrown('b'),
                },
                extra_policy=extra_policy,
            ),
            extra_move=None,
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )

    if extra_policy == ExtraCollect():
        pytest.raises(ValueError, loader_getter).match(
            "Cannot create loader that collect extra data if InputFigure does not take extra data"
        )
        return

    loader = loader_getter()
    assert loader({'a': 1, 'b': 2}) == gauge(1, 2)

    if extra_policy == ExtraSkip():
        assert loader({'a': 1, 'b': 2, 'c': 3}) == gauge(1, 2)
    if extra_policy == ExtraForbid():
        raises_path(
            ExtraFieldsError({'c'}),
            lambda: loader({'a': 1, 'b': 2, 'c': 3}),
            path=[],
        )

    raises_path(
        LoadError(),
        lambda: loader({'a': 1, 'b': LoadError()}),
        path=['b'] if debug_path else [],
    )

    raises_path(
        NoRequiredFieldsError(['b']),
        lambda: loader({'a': 1}),
        path=[],
    )

    raises_path(
        TypeLoadError(dict),
        lambda: loader("bad input value"),
        path=[],
    )


@pytest.mark.parametrize('extra_policy', [ExtraSkip(), ExtraForbid()])
def test_direct_list(debug_ctx, debug_path, extra_policy):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
        ),
        name_layout=InputNameLayout(
            crown=InpListCrown(
                [
                    InpFieldCrown('a'),
                    InpFieldCrown('b'),
                ],
                extra_policy=extra_policy,
            ),
            extra_move=None,
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )

    loader = loader_getter()
    assert loader([1, 2]) == gauge(1, 2)

    if extra_policy == ExtraSkip():
        assert loader([1, 2, 3]) == gauge(1, 2)

    if extra_policy == ExtraForbid():
        raises_path(
            ExtraItemsError(2),
            lambda: loader([1, 2, 3]),
            path=[],
        )

    raises_path(
        NoRequiredItemsError(2),
        lambda: loader([10]),
        path=[],
    )

    raises_path(
        TypeLoadError(list),
        lambda: loader("bad input value"),
        path=[],
    )


def test_extra_forbid(debug_ctx, debug_path):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                    'b': InpFieldCrown('b'),
                },
                extra_policy=ExtraForbid(),
            ),
            extra_move=None,
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )

    loader = loader_getter()

    raises_path(
        ExtraFieldsError({'c'}),
        lambda: loader({'a': 1, 'b': 2, 'c': 3}),
        path=[],
    )
    raises_path(
        ExtraFieldsError({'c', 'd'}),
        lambda: loader({'a': 1, 'b': 2, 'c': 3, 'd': 4}),
        path=[],
    )


def test_creation(debug_ctx, debug_path, extra_policy):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_ONLY, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
            field('c', ParamKind.POS_OR_KW, is_required=False),
            field('d', ParamKind.KW_ONLY, is_required=True),
            field('e', ParamKind.KW_ONLY, is_required=False),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                    'b': InpFieldCrown('b'),
                    'c': InpFieldCrown('c'),
                    'd': InpFieldCrown('d'),
                    'e': InpFieldCrown('e'),
                },
                extra_policy=extra_policy,
            ),
            extra_move=ExtraKwargs(),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader({'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5}) == gauge(1, 2, c=3, d=4, e=5)


def test_extra_kwargs(debug_ctx, debug_path):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_ONLY, is_required=True),
            kwargs=ParamKwargs(Any),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                },
                extra_policy=ExtraCollect(),
            ),
            extra_move=ExtraKwargs(),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader({'a': 1}) == gauge(1)
    assert loader({'a': 1, 'b': 2}) == gauge(1, b=2)


def test_wild_extra_targets(debug_ctx, debug_path):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                },
                extra_policy=ExtraCollect(),
            ),
            extra_move=ExtraTargets(('b',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )

    pytest.raises(ValueError, loader_getter).match(
        full_match_regex_str("ExtraTargets ['b'] are attached to non-existing fields")
    )


@parametrize_bool('is_required')
def test_extra_targets_one(debug_ctx, debug_path, is_required):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=is_required),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                },
                extra_policy=ExtraCollect(),
            ),
            extra_move=ExtraTargets(('b',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader({'a': 1}) == gauge(1, {})
    assert loader({'a': 1, 'c': 2}) == gauge(1, {'c': 2})
    assert loader({'a': 1, 'b': 2}) == gauge(1, {'b': 2})
    assert loader({'a': 1, 'b': 2, 'c': 3}) == gauge(1, {'b': 2, 'c': 3})


@parametrize_bool('is_required_first', 'is_required_second')
def test_extra_targets_two(debug_ctx, debug_path, is_required_first, is_required_second):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=is_required_first),
            field('c', ParamKind.KW_ONLY, is_required=is_required_second),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                },
                extra_policy=ExtraCollect(),
            ),
            extra_move=ExtraTargets(('b', 'c')),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader({'a': 1}) == gauge(1, {}, c={})
    assert loader({'a': 1, 'd': 2}) == gauge(1, {'d': 2}, c={'d': 2})
    assert loader({'a': 1, 'b': 2}) == gauge(1, {'b': 2}, c={'b': 2})
    assert loader({'a': 1, 'c': 2}) == gauge(1, {'c': 2}, c={'c': 2})
    assert loader({'a': 1, 'b': 2, 'c': 3}) == gauge(1, {'b': 2, 'c': 3}, c={'b': 2, 'c': 3})
    assert loader({'a': 1, 'b': 2, 'c': 3, 'd': 4}) == gauge(1, {'b': 2, 'c': 3, 'd': 4}, c={'b': 2, 'c': 3, 'd': 4})


def test_extra_saturate(debug_ctx, debug_path):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_ONLY, is_required=True),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                },
                extra_policy=ExtraCollect(),
            ),
            extra_move=ExtraSaturate(Gauge.saturate),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader({'a': 1}) == gauge(1).with_extra({})
    assert loader({'a': 1, 'b': 2}) == gauge(1).with_extra({'b': 2})


def test_mapping_and_extra_kwargs(debug_ctx, debug_path):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=False),
            kwargs=ParamKwargs(Any),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                    'm_b': InpFieldCrown('b'),
                },
                extra_policy=ExtraCollect(),
            ),
            extra_move=ExtraKwargs(),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    raises_path(
        NoRequiredFieldsError(['m_a']),
        lambda: loader({'a': 1, 'b': 2}),
        path=[],
    )

    assert loader({'m_a': 1, 'b': 'this value is not loaded'}) == gauge(1, b='this value is not loaded')
    assert loader({'m_a': 1, 'm_b': 2}) == gauge(1, b=2)
    pytest.raises(
        TypeError, lambda: loader({'m_a': 1, 'm_b': 2, 'b': 3}),
    ).match("got multiple values for keyword argument 'b'")


def test_skipped_required_field(debug_ctx, debug_path, extra_policy):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                },
                extra_policy=extra_policy,
            ),
            extra_move=None,
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, loader_getter).match(full_match_regex_str("Required fields ['b'] are skipped"))

    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                },
                extra_policy=extra_policy,
            ),
            extra_move=ExtraTargets(('b',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    loader_getter()


def test_extra_target_at_crown(debug_ctx, debug_path, extra_policy):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=True),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                    'm_b': InpFieldCrown('b'),
                },
                extra_policy=extra_policy,
            ),
            extra_move=ExtraTargets(('b',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, loader_getter).match(
        full_match_regex_str("Extra targets ['b'] are found at crown")
    )

    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=False),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                    'm_b': InpFieldCrown('b'),
                },
                extra_policy=extra_policy,
            ),
            extra_move=ExtraTargets(('b',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, loader_getter).match(
        full_match_regex_str("Extra targets ['b'] are found at crown")
    )


def test_optional_fields_at_list(debug_ctx, debug_path, extra_policy):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=False),
        ),
        name_layout=InputNameLayout(
            crown=InpListCrown(
                [
                    InpFieldCrown('a'),
                    InpFieldCrown('b'),
                ],
                extra_policy=extra_policy,
            ),
            extra_move=None,
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, loader_getter).match(
        full_match_regex_str("Optional fields ['b'] are found at list crown")
    )


@parametrize_bool('is_required')
def test_flat_mapping(debug_ctx, debug_path, is_required):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('b', ParamKind.POS_OR_KW, is_required=False),
            field('e', ParamKind.KW_ONLY, is_required=is_required),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'm_a': InpFieldCrown('a'),
                    'm_b': InpFieldCrown('b'),
                },
                extra_policy=ExtraCollect(),
            ),
            extra_move=ExtraTargets(('e',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    raises_path(
        NoRequiredFieldsError(['m_a']),
        lambda: loader({'a': 1, 'b': 2}),
        path=[],
    )

    assert loader({'m_a': 1, 'b': 2}) == gauge(1, e={'b': 2})
    assert loader({'m_a': 1, 'm_b': 2}) == gauge(1, b=2, e={})
    assert loader({'m_a': 1, 'm_b': 2, 'b': 3}) == gauge(1, b=2, e={'b': 3})


COMPLEX_STRUCTURE_FIGURE = figure(
    field('a', ParamKind.KW_ONLY, is_required=True),
    field('b', ParamKind.KW_ONLY, is_required=True),
    field('c', ParamKind.KW_ONLY, is_required=True),
    field('d', ParamKind.KW_ONLY, is_required=True),
    field('e', ParamKind.KW_ONLY, is_required=True),
    field('f', ParamKind.KW_ONLY, is_required=True),
    field('extra', ParamKind.KW_ONLY, is_required=True),
)

COMPLEX_STRUCTURE_CROWN = InpDictCrown(
    {
        'z': InpDictCrown(
            {
                'y': InpFieldCrown('a'),
                'x': InpFieldCrown('b'),
            },
            extra_policy=ExtraCollect(),
        ),
        'w': InpFieldCrown('c'),
        'v': InpListCrown(
            [
                InpFieldCrown('d'),
                InpDictCrown(
                    {
                        'u': InpFieldCrown('e'),
                    },
                    extra_policy=ExtraCollect(),
                ),
                InpListCrown(
                    [
                        InpFieldCrown('f')
                    ],
                    extra_policy=ExtraForbid(),
                )
            ],
            extra_policy=ExtraForbid(),
        ),
    },
    extra_policy=ExtraCollect(),
)


def test_structure_flattening(debug_ctx, debug_path):
    loader_getter = make_loader_getter(
        fig=COMPLEX_STRUCTURE_FIGURE,
        name_layout=InputNameLayout(
            crown=COMPLEX_STRUCTURE_CROWN,
            extra_move=ExtraTargets(('extra',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader(
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

    assert loader(
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
        TypeLoadError(dict),
        lambda: loader(
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
        TypeLoadError(list),
        lambda: loader(
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
    loader_getter = make_loader_getter(
        fig=COMPLEX_STRUCTURE_FIGURE,
        name_layout=InputNameLayout(
            crown=COMPLEX_STRUCTURE_CROWN,
            extra_move=ExtraTargets(('extra',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

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

    _replace_value_by_path(data, error_path, LoadError())

    raises_path(
        LoadError(),
        lambda: loader(data),
        path=error_path if debug_path else []
    )


def test_none_crown_at_dict_crown(debug_ctx, debug_path, extra_policy):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
            field('extra', ParamKind.KW_ONLY, is_required=True),
        ),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {
                    'a': InpFieldCrown('a'),
                    'b': InpNoneCrown(),
                },
                extra_policy=extra_policy,
            ),
            extra_move=ExtraTargets(('extra',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader({'a': 1}) == gauge(1, extra={})
    assert loader({'a': 1, 'b': 2}) == gauge(1, extra={})

    if extra_policy == ExtraSkip():
        assert loader({'a': 1, 'b': 2, 'c': 3}) == gauge(1, extra={})

    if extra_policy == ExtraCollect():
        assert loader({'a': 1, 'b': 2, 'c': 3}) == gauge(1, extra={'c': 3})

    if extra_policy == ExtraForbid():
        raises_path(
            ExtraFieldsError({'c'}),
            lambda: loader({'a': 1, 'b': 2, 'c': 3}),
            path=[],
        )


@pytest.mark.parametrize('extra_policy', [ExtraSkip(), ExtraForbid()])
def test_none_crown_at_list_crown(debug_ctx, debug_path, extra_policy):
    loader_getter = make_loader_getter(
        fig=figure(
            field('a', ParamKind.POS_OR_KW, is_required=True),
        ),
        name_layout=InputNameLayout(
            crown=InpListCrown(
                [
                    InpNoneCrown(),
                    InpFieldCrown('a'),
                    InpNoneCrown(),
                ],
                extra_policy=extra_policy,
            ),
            extra_move=None,
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader([1, 2, 3]) == gauge(2)

    raises_path(
        NoRequiredItemsError(3),
        lambda: loader([1, 2]),
        path=[],
    )

    if extra_policy == ExtraSkip():
        assert loader([1, 2, 3, 4]) == gauge(2)

    if extra_policy == ExtraForbid():
        raises_path(
            ExtraItemsError(3),
            lambda: loader([1, 2, 3, 4]),
            path=[],
        )
