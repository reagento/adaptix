from collections.abc import Mapping as CollectionsMapping, Sequence as CollectionsSequence
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Callable, Dict, Optional

import pytest
from tests_helpers import DebugCtx, TestRetort, full_match_regex_str, parametrize_bool, raises_exc

from adaptix import DebugTrail, ExtraKwargs, Loader, bound
from adaptix._internal.common import VarTuple
from adaptix._internal.load_error import AggregateLoadError, ExcludedTypeLoadError, ValueLoadError
from adaptix._internal.model_tools.definitions import InputField, InputShape, NoDefault, Param, ParamKind, ParamKwargs
from adaptix._internal.morphing.model.crown_definitions import (
    ExtraCollect,
    ExtraForbid,
    ExtraSaturate,
    ExtraSkip,
    ExtraTargets,
    InpDictCrown,
    InpFieldCrown,
    InpListCrown,
    InpNoneCrown,
    InputNameLayout,
    InputNameLayoutRequest,
)
from adaptix._internal.morphing.model.definitions import InputShapeRequest
from adaptix._internal.morphing.model.loader_provider import ModelLoaderProvider
from adaptix._internal.provider.provider_template import ValueProvider
from adaptix._internal.provider.request_cls import LoaderRequest
from adaptix._internal.struct_trail import extend_trail
from adaptix.load_error import (
    ExtraFieldsError,
    ExtraItemsError,
    LoadError,
    NoRequiredFieldsError,
    NoRequiredItemsError,
    TypeLoadError,
)


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


@dataclass
class TestField:
    id: str
    param_kind: ParamKind
    is_required: bool


def shape(*fields: TestField, kwargs: Optional[ParamKwargs] = None):
    return InputShape(
        fields=tuple(
            InputField(
                type=int,
                id=fld.id,
                default=NoDefault(),
                is_required=fld.is_required,
                metadata=MappingProxyType({}),
                original=None,
            )
            for fld in fields
        ),
        constructor=gauge,
        kwargs=kwargs,
        overriden_types=frozenset(fld.id for fld in fields),
        params=tuple(
            Param(
                field_id=fld.id,
                name=fld.id,
                kind=fld.param_kind,
            )
            for fld in fields
        ),
    )


def int_loader(data):
    if isinstance(data, BaseException):
        raise data
    return data


def make_loader_getter(
    *,
    shape: InputShape,
    name_layout: InputNameLayout,
    debug_trail: DebugTrail,
    strict_coercion: bool = True,
    debug_ctx: DebugCtx,
) -> Callable[[], Loader]:
    def getter():
        retort = TestRetort(
            recipe=[
                ValueProvider(InputShapeRequest, shape),
                ValueProvider(InputNameLayoutRequest, name_layout),
                bound(int, ValueProvider(LoaderRequest, int_loader)),
                ModelLoaderProvider(),
                debug_ctx.accum,
            ]
        )

        loader = retort.replace(
            debug_trail=debug_trail,
            strict_coercion=strict_coercion,
        ).get_loader(
            Gauge,
        )
        return loader

    return getter


@pytest.fixture(params=[ExtraSkip(), ExtraForbid(), ExtraCollect()])
def extra_policy(request):
    return request.param


def test_direct(debug_ctx, debug_trail, extra_policy, trail_select):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=True),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )

    if extra_policy == ExtraCollect():
        pytest.raises(ValueError, loader_getter).match(
            "Cannot create loader that collect extra data if InputShape does not take extra data"
        )
        return

    loader = loader_getter()
    assert loader({'a': 1, 'b': 2}) == gauge(1, 2)

    if extra_policy == ExtraSkip():
        assert loader({'a': 1, 'b': 2, 'c': 3}) == gauge(1, 2)
    if extra_policy == ExtraForbid():
        data = {'a': 1, 'b': 2, 'c': 3}
        raises_exc(
            trail_select(
                disable=ExtraFieldsError({'c'}, data),
                first=ExtraFieldsError({'c'}, data),
                all=AggregateLoadError(
                    f'while loading model {Gauge}',
                    [ExtraFieldsError({'c'}, data)],
                ),
            ),
            lambda: loader(data),
        )

    raises_exc(
        trail_select(
            disable=LoadError(),
            first=extend_trail(LoadError(), ['b']),
            all=AggregateLoadError(
                f'while loading model {Gauge}',
                [extend_trail(LoadError(), ['b'])],
            ),
        ),
        lambda: loader({'a': 1, 'b': LoadError()}),
    )

    data = {'a': 1}
    raises_exc(
        trail_select(
            disable=NoRequiredFieldsError({'b'}, data),
            first=NoRequiredFieldsError({'b'}, data),
            all=AggregateLoadError(
                f'while loading model {Gauge}',
                [NoRequiredFieldsError({'b'}, data)],
            ),
        ),
        lambda: loader({'a': 1}),
    )

    raises_exc(
        trail_select(
            disable=TypeLoadError(CollectionsMapping, "bad input value"),
            first=TypeLoadError(CollectionsMapping, "bad input value"),
            all=AggregateLoadError(
                f'while loading model {Gauge}',
                [TypeLoadError(CollectionsMapping, "bad input value")],
            ),
        ),
        lambda: loader("bad input value"),
    )


@pytest.mark.parametrize('extra_policy', [ExtraSkip(), ExtraForbid()])
def test_direct_list(debug_ctx, debug_trail, extra_policy, trail_select, strict_coercion):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=True),
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
        debug_trail=debug_trail,
        strict_coercion=strict_coercion,
        debug_ctx=debug_ctx,
    )

    loader = loader_getter()
    assert loader([1, 2]) == gauge(1, 2)

    if extra_policy == ExtraSkip():
        assert loader([1, 2, 3]) == gauge(1, 2)

    if extra_policy == ExtraForbid():
        data = [1, 2, 3]
        raises_exc(
            trail_select(
                disable=ExtraItemsError(2, data),
                first=ExtraItemsError(2, data),
                all=AggregateLoadError(
                    f'while loading model {Gauge}',
                    [ExtraItemsError(2, data)],
                ),
            ),
            lambda: loader(data),
        )

    data = [10]
    raises_exc(
        trail_select(
            disable=NoRequiredItemsError(2, data),
            first=NoRequiredItemsError(2, data),
            all=AggregateLoadError(
                f'while loading model {Gauge}',
                [NoRequiredItemsError(2, data)],
            ),
        ),
        lambda: loader(data),
    )

    if strict_coercion:
        raises_exc(
            trail_select(
                disable=ExcludedTypeLoadError(CollectionsSequence, str, 'ab'),
                first=ExcludedTypeLoadError(CollectionsSequence, str, 'ab'),
                all=AggregateLoadError(
                    f'while loading model {Gauge}',
                    [ExcludedTypeLoadError(CollectionsSequence, str, 'ab')],
                ),
            ),
            lambda: loader('ab'),
        )
    else:
        assert loader("ab") == gauge('a', 'b')

    raises_exc(
        trail_select(
            disable=TypeLoadError(CollectionsSequence, 123),
            first=TypeLoadError(CollectionsSequence, 123),
            all=AggregateLoadError(
                f'while loading model {Gauge}',
                [TypeLoadError(CollectionsSequence, 123)],
            ),
        ),
        lambda: loader(123),
    )


def test_extra_forbid(debug_ctx, debug_trail, trail_select):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=True),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )

    loader = loader_getter()

    data = {'a': 1, 'b': 2, 'c': 3}
    raises_exc(
        trail_select(
            disable=ExtraFieldsError({'c'}, data),
            first=ExtraFieldsError({'c'}, data),
            all=AggregateLoadError(
                f'while loading model {Gauge}',
                [ExtraFieldsError({'c'}, data)],
            )
        ),
        lambda: loader(data),
    )
    data = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    raises_exc(
        trail_select(
            disable=ExtraFieldsError({'c', 'd'}, data),
            first=ExtraFieldsError({'c', 'd'}, data),
            all=AggregateLoadError(
                f'while loading model {Gauge}',
                [ExtraFieldsError({'c', 'd'}, data)],
            )
        ),
        lambda: loader(data),
    )


def test_creation(debug_ctx, debug_trail, extra_policy):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_ONLY, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=True),
            TestField('c', ParamKind.POS_OR_KW, is_required=False),
            TestField('d', ParamKind.KW_ONLY, is_required=True),
            TestField('e', ParamKind.KW_ONLY, is_required=False),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader({'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5}) == gauge(1, 2, c=3, d=4, e=5)


def test_extra_kwargs(debug_ctx, debug_trail):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_ONLY, is_required=True),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader({'a': 1}) == gauge(1)
    assert loader({'a': 1, 'b': 2}) == gauge(1, b=2)


def test_wild_extra_targets(debug_ctx, debug_trail):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )

    pytest.raises(ValueError, loader_getter).match(
        full_match_regex_str("ExtraTargets ['b'] are attached to non-existing fields")
    )


@parametrize_bool('is_required')
def test_extra_targets_one(debug_ctx, debug_trail, is_required):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=is_required),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader({'a': 1}) == gauge(1, {})
    assert loader({'a': 1, 'c': 2}) == gauge(1, {'c': 2})
    assert loader({'a': 1, 'b': 2}) == gauge(1, {'b': 2})
    assert loader({'a': 1, 'b': 2, 'c': 3}) == gauge(1, {'b': 2, 'c': 3})


@parametrize_bool('is_required_first', 'is_required_second')
def test_extra_targets_two(debug_ctx, debug_trail, is_required_first, is_required_second):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=is_required_first),
            TestField('c', ParamKind.KW_ONLY, is_required=is_required_second),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader({'a': 1}) == gauge(1, {}, c={})
    assert loader({'a': 1, 'd': 2}) == gauge(1, {'d': 2}, c={'d': 2})
    assert loader({'a': 1, 'b': 2}) == gauge(1, {'b': 2}, c={'b': 2})
    assert loader({'a': 1, 'c': 2}) == gauge(1, {'c': 2}, c={'c': 2})
    assert loader({'a': 1, 'b': 2, 'c': 3}) == gauge(1, {'b': 2, 'c': 3}, c={'b': 2, 'c': 3})
    assert loader({'a': 1, 'b': 2, 'c': 3, 'd': 4}) == gauge(1, {'b': 2, 'c': 3, 'd': 4}, c={'b': 2, 'c': 3, 'd': 4})


def test_extra_saturate(debug_ctx, debug_trail):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_ONLY, is_required=True),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader({'a': 1}) == gauge(1).with_extra({})
    assert loader({'a': 1, 'b': 2}) == gauge(1).with_extra({'b': 2})


def test_mapping_and_extra_kwargs(debug_ctx, debug_trail, trail_select):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=False),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    data = {'a': 1, 'b': 2}
    raises_exc(
        trail_select(
            disable=NoRequiredFieldsError({'m_a'}, data),
            first=NoRequiredFieldsError({'m_a'}, data),
            all=AggregateLoadError(f'while loading model {Gauge}', [NoRequiredFieldsError({'m_a'}, data)])
        ),
        lambda: loader(data),
    )

    assert loader({'m_a': 1, 'b': 'this value is not loaded'}) == gauge(1, b='this value is not loaded')
    assert loader({'m_a': 1, 'm_b': 2}) == gauge(1, b=2)
    pytest.raises(
        TypeError, lambda: loader({'m_a': 1, 'm_b': 2, 'b': 3}),
    ).match("got multiple values for keyword argument 'b'")


def test_skipped_required_field(debug_ctx, debug_trail, extra_policy):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=True),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, loader_getter).match(full_match_regex_str("Required fields ['b'] are skipped"))

    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=True),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    loader_getter()


def test_extra_target_at_crown(debug_ctx, debug_trail, extra_policy):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=True),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, loader_getter).match(
        full_match_regex_str("Extra targets ['b'] are found at crown")
    )

    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=False),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, loader_getter).match(
        full_match_regex_str("Extra targets ['b'] are found at crown")
    )


def test_optional_fields_at_list(debug_ctx, debug_trail, extra_policy):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=False),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, loader_getter).match(
        full_match_regex_str("Optional fields ['b'] are found at list crown")
    )


@parametrize_bool('is_required')
def test_flat_mapping(debug_ctx, debug_trail, is_required, trail_select):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=False),
            TestField('e', ParamKind.KW_ONLY, is_required=is_required),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    data = {'a': 1, 'b': 2}
    raises_exc(
        trail_select(
            disable=NoRequiredFieldsError({'m_a'}, data),
            first=NoRequiredFieldsError({'m_a'}, data),
            all=AggregateLoadError(f'while loading model {Gauge}', [NoRequiredFieldsError({'m_a'}, data)])
        ),
        lambda: loader(data),
    )

    assert loader({'m_a': 1, 'b': 2}) == gauge(1, e={'b': 2})
    assert loader({'m_a': 1, 'm_b': 2}) == gauge(1, b=2, e={})
    assert loader({'m_a': 1, 'm_b': 2, 'b': 3}) == gauge(1, b=2, e={'b': 3})


COMPLEX_STRUCTURE_SHAPE = shape(
    TestField('a', ParamKind.KW_ONLY, is_required=True),
    TestField('b', ParamKind.KW_ONLY, is_required=True),
    TestField('c', ParamKind.KW_ONLY, is_required=True),
    TestField('d', ParamKind.KW_ONLY, is_required=True),
    TestField('e', ParamKind.KW_ONLY, is_required=True),
    TestField('f', ParamKind.KW_ONLY, is_required=True),
    TestField('extra', ParamKind.KW_ONLY, is_required=True),
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


def test_structure_flattening(debug_ctx, debug_trail, trail_select):
    loader_getter = make_loader_getter(
        shape=COMPLEX_STRUCTURE_SHAPE,
        name_layout=InputNameLayout(
            crown=COMPLEX_STRUCTURE_CROWN,
            extra_move=ExtraTargets(('extra',)),
        ),
        debug_trail=debug_trail,
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

    raises_exc(
        trail_select(
            disable=TypeLoadError(CollectionsMapping, 'this is not a dict'),
            first=extend_trail(TypeLoadError(CollectionsMapping, 'this is not a dict'), ['z']),
            all=AggregateLoadError(
                f'while loading model {Gauge}',
                [extend_trail(TypeLoadError(CollectionsMapping, 'this is not a dict'), ['z'])],
            ),
        ),
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
    )

    raises_exc(
        trail_select(
            disable=TypeLoadError(CollectionsSequence, None),
            first=extend_trail(TypeLoadError(CollectionsSequence, None), ['v']),
            all=AggregateLoadError(
                f'while loading model {Gauge}',
                [extend_trail(TypeLoadError(CollectionsSequence, None), ['v'])],
            ),
        ),
        lambda: loader(
            {
                'z': {
                    'y': 1,
                    'x': 2,
                },
                'w': 3,
                'v': None,
            }
        ),
    )

    raises_exc(
        trail_select(
            disable=ExcludedTypeLoadError(CollectionsSequence, str, 'this is not a list'),
            first=extend_trail(ExcludedTypeLoadError(CollectionsSequence, str, 'this is not a list'), ['v']),
            all=AggregateLoadError(
                f'while loading model {Gauge}',
                [extend_trail(ExcludedTypeLoadError(CollectionsSequence, str, 'this is not a list'), ['v'])],
            ),
        ),
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
def test_error_path_at_complex_structure(debug_ctx, debug_trail, error_path, trail_select):
    loader_getter = make_loader_getter(
        shape=COMPLEX_STRUCTURE_SHAPE,
        name_layout=InputNameLayout(
            crown=COMPLEX_STRUCTURE_CROWN,
            extra_move=ExtraTargets(('extra',)),
        ),
        debug_trail=debug_trail,
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

    raises_exc(
        trail_select(
            disable=LoadError(),
            first=extend_trail(LoadError(), error_path),
            all=AggregateLoadError(f'while loading model {Gauge}', [extend_trail(LoadError(), error_path)]),
        ),
        lambda: loader(data),
    )


def test_none_crown_at_dict_crown(debug_ctx, debug_trail, extra_policy, trail_select):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('extra', ParamKind.KW_ONLY, is_required=True),
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
        debug_trail=debug_trail,
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
        data = {'a': 1, 'b': 2, 'c': 3}
        raises_exc(
            trail_select(
                disable=ExtraFieldsError({'c'}, data),
                first=ExtraFieldsError({'c'}, data),
                all=AggregateLoadError(f'while loading model {Gauge}', [ExtraFieldsError({'c'}, data)]),
            ),
            lambda: loader(data),
        )


@pytest.mark.parametrize('extra_policy', [ExtraSkip(), ExtraForbid()])
def test_none_crown_at_list_crown(debug_ctx, debug_trail, extra_policy, trail_select):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
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
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    assert loader([1, 2, 3]) == gauge(2)

    data = [1, 2]
    raises_exc(
        trail_select(
            disable=NoRequiredItemsError(3, data),
            first=NoRequiredItemsError(3, data),
            all=AggregateLoadError(f'while loading model {Gauge}', [NoRequiredItemsError(3, data)]),
        ),
        lambda: loader(data),
    )

    if extra_policy == ExtraSkip():
        assert loader([1, 2, 3, 4]) == gauge(2)

    if extra_policy == ExtraForbid():
        data = [1, 2, 3, 4]
        raises_exc(
            trail_select(
                disable=ExtraItemsError(3, data),
                first=ExtraItemsError(3, data),
                all=AggregateLoadError(f'while loading model {Gauge}', [ExtraItemsError(3, data)]),
            ),
            lambda: loader(data),
        )


def test_exception_collection(debug_ctx):
    loader_getter = make_loader_getter(
        shape=shape(
            TestField('a', ParamKind.POS_OR_KW, is_required=True),
            TestField('b', ParamKind.POS_OR_KW, is_required=True),
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
        debug_trail=DebugTrail.ALL,
        debug_ctx=debug_ctx,
    )
    loader = loader_getter()

    raises_exc(
        AggregateLoadError(
            f'while loading model {Gauge}',
            [
                extend_trail(ValueLoadError('error at a', ...), ['a']),
                extend_trail(ValueLoadError('error at b', ...), ['b']),
            ]
        ),
        lambda: loader({'a': ValueLoadError('error at a', ...), 'b': ValueLoadError('error at b', ...)}),
    )

    data = {'a': ValueLoadError('error at a', ...)}
    raises_exc(
        AggregateLoadError(
            f'while loading model {Gauge}',
            [
                extend_trail(ValueLoadError('error at a', ...), ['a']),
                NoRequiredFieldsError({'b'}, data),
            ]
        ),
        lambda: loader(data),
    )

    data = {'a': ValueLoadError('error at a', ...), 'c': 3}
    raises_exc(
        AggregateLoadError(
            f'while loading model {Gauge}',
            [
                extend_trail(ValueLoadError('error at a', ...), ['a']),
                NoRequiredFieldsError({'b'}, data),
                ExtraFieldsError({'c'}, data),
            ]
        ),
        lambda: loader(data),
    )


def test_empty_dict(debug_ctx, debug_trail, extra_policy, trail_select):
    loader_getter = make_loader_getter(
        shape=shape(),
        name_layout=InputNameLayout(
            crown=InpDictCrown(
                {},
                extra_policy=extra_policy,
            ),
            extra_move=None,
        ),
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
    )

    if extra_policy == ExtraCollect():
        pytest.raises(ValueError, loader_getter).match(
            "Cannot create loader that collect extra data if InputShape does not take extra data"
        )
        return

    loader = loader_getter()
    assert loader({}) == gauge()

    raises_exc(
        trail_select(
            disable=TypeLoadError(CollectionsMapping, []),
            first=TypeLoadError(CollectionsMapping, []),
            all=AggregateLoadError(f'while loading model {Gauge}', [TypeLoadError(CollectionsMapping, [])]),
        ),
        lambda: loader([]),
    )

    raises_exc(
        trail_select(
            disable=TypeLoadError(CollectionsMapping, None),
            first=TypeLoadError(CollectionsMapping, None),
            all=AggregateLoadError(f'while loading model {Gauge}', [TypeLoadError(CollectionsMapping, None)]),
        ),
        lambda: loader(None),
    )


@pytest.mark.parametrize('extra_policy', [ExtraSkip(), ExtraForbid()])
def test_empty_list(debug_ctx, debug_trail, extra_policy, trail_select, strict_coercion):
    loader_getter = make_loader_getter(
        shape=shape(),
        name_layout=InputNameLayout(
            crown=InpListCrown(
                [],
                extra_policy=extra_policy,
            ),
            extra_move=None,
        ),
        debug_trail=debug_trail,
        debug_ctx=debug_ctx,
        strict_coercion=strict_coercion,
    )

    loader = loader_getter()
    assert loader([]) == gauge()

    raises_exc(
        trail_select(
            disable=TypeLoadError(CollectionsSequence, {}),
            first=TypeLoadError(CollectionsSequence, {}),
            all=AggregateLoadError(f'while loading model {Gauge}', [TypeLoadError(CollectionsSequence, {})]),
        ),
        lambda: loader({}),
    )

    raises_exc(
        trail_select(
            disable=TypeLoadError(CollectionsSequence, None),
            first=TypeLoadError(CollectionsSequence, None),
            all=AggregateLoadError(f'while loading model {Gauge}', [TypeLoadError(CollectionsSequence, None)]),
        ),
        lambda: loader(None),
    )

    if strict_coercion:
        raises_exc(
            trail_select(
                disable=ExcludedTypeLoadError(CollectionsSequence, str, ''),
                first=ExcludedTypeLoadError(CollectionsSequence, str, ''),
                all=AggregateLoadError(
                    f'while loading model {Gauge}',
                    [ExcludedTypeLoadError(CollectionsSequence, str, '')],
                ),
            ),
            lambda: loader(''),
        )
    else:
        assert loader('') == gauge()

        if extra_policy == ExtraSkip():
            assert loader('abc') == gauge()
        elif extra_policy == ExtraForbid():
            raises_exc(
                trail_select(
                    disable=ExtraItemsError(0, 'abc'),
                    first=ExtraItemsError(0, 'abc'),
                    all=AggregateLoadError(f'while loading model {Gauge}', [ExtraItemsError(0, 'abc')]),
                ),
                lambda: loader('abc'),
            )
