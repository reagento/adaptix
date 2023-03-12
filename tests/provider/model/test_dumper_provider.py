import re
from dataclasses import dataclass
from types import MappingProxyType, SimpleNamespace
from typing import Any, Callable, Dict, Optional, Type

import pytest

from adaptix import Dumper, bound
from adaptix._internal.common import Catchable
from adaptix._internal.model_tools import (
    Accessor,
    AttrAccessor,
    DefaultFactory,
    DefaultValue,
    ItemAccessor,
    NoDefault,
    OutputField,
    OutputFigure,
)
from adaptix._internal.provider import (
    BuiltinOutputCreationMaker,
    DumperRequest,
    ModelDumperProvider,
    NameSanitizer,
    OutputFigureRequest,
    OutputNameLayoutRequest,
    TypeHintLoc,
    ValueProvider,
    make_output_extraction,
)
from adaptix._internal.provider.model import OutDictCrown, OutFieldCrown, OutListCrown, OutNoneCrown, OutputNameLayout
from adaptix._internal.provider.model.crown_definitions import ExtraExtract, ExtraTargets
from adaptix._internal.struct_path import Attr, PathElement, PathElementMarker
from adaptix._internal.utils import SingletonMeta
from tests_helpers import DebugCtx, TestRetort, full_match_regex_str, parametrize_bool, raises_path


def field(name: str, accessor: Accessor):
    return OutputField(
        type=int,
        name=name,
        default=NoDefault(),
        accessor=accessor,
        metadata=MappingProxyType({}),
    )


def figure(*fields: OutputField):
    return OutputFigure(fields=fields, overriden_types=frozenset(fld.name for fld in fields))


def int_dumper(data):
    if isinstance(data, BaseException):
        raise data
    return data


class Dummy:
    def __init__(self, items: Optional[Dict[str, Any]] = None, **kwargs: Any):
        if items is None:
            items = {}

        self.items = items

        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, item):
        return self.items[item]


def dummy_items(**kwargs: Any):
    return Dummy(items=kwargs)


def make_dumper_getter(
    fig: OutputFigure,
    name_layout: OutputNameLayout,
    debug_path: bool,
    debug_ctx: DebugCtx,
) -> Callable[[], Dumper]:
    def getter():
        retort = TestRetort(
            recipe=[
                ValueProvider(OutputFigureRequest, fig),
                ValueProvider(OutputNameLayoutRequest, name_layout),
                bound(int, ValueProvider(DumperRequest, int_dumper)),
                ModelDumperProvider(NameSanitizer(), make_output_extraction, BuiltinOutputCreationMaker()),
                debug_ctx.accum,
            ]
        )

        dumper = retort.replace(
            debug_path=debug_path
        ).get_dumper(
            Dummy,
        )
        return dumper

    return getter


class Skip(metaclass=SingletonMeta):
    pass


def skipper(value):
    return value != Skip()


@dataclass(eq=False)
class SomeError(Exception):
    value: int = 0


def stub(value):
    return value


@dataclass
class AccessSchema:
    dummy: Callable
    accessor_maker: Callable[[str, bool], Accessor]
    access_error: Type[Exception]
    path_elem_maker: Callable[[str], Any]


class MyAccessError(Exception):
    pass


@dataclass
class MyPathElemMarker(PathElementMarker):
    value: Any


@dataclass
class MyAccessor(Accessor):
    value: Any
    is_required: bool

    @property
    def getter(self) -> Callable[[Any], Any]:
        def my_getter(obj):
            try:
                return getattr(obj, self.value)
            except AttributeError:
                raise MyAccessError

        return my_getter

    @property
    def access_error(self) -> Optional[Catchable]:
        return None if self.is_required else MyAccessError

    @property
    def path_element(self) -> PathElement:
        return MyPathElemMarker(self.value)

    def __hash__(self) -> int:
        return hash(self.value)


@pytest.fixture(
    params=[
        AccessSchema(
            dummy=Dummy, accessor_maker=AttrAccessor, access_error=AttributeError, path_elem_maker=Attr,
        ),
        AccessSchema(
            dummy=dummy_items, accessor_maker=ItemAccessor, access_error=KeyError, path_elem_maker=stub,
        ),
        AccessSchema(
            dummy=Dummy, accessor_maker=MyAccessor, access_error=MyAccessError, path_elem_maker=MyPathElemMarker,
        )
    ],
    ids=['attrs', 'items', 'custom'],
)
def acc_schema(request):
    return request.param


@parametrize_bool('is_required_a', 'is_required_b')
def test_flat(debug_ctx, debug_path, is_required_a, is_required_b, acc_schema):
    dumper_getter = make_dumper_getter(
        fig=figure(
            field('a', acc_schema.accessor_maker('a', is_required_a)),
            field('b', acc_schema.accessor_maker('b', is_required_b)),
        ),
        name_layout=OutputNameLayout(
            crown=OutDictCrown(
                {
                    'a': OutFieldCrown('a'),
                    'b': OutFieldCrown('b'),
                },
                sieves={
                    'b': skipper,
                },
            ),
            extra_move=None,
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )

    dumper = dumper_getter()

    assert dumper(acc_schema.dummy(a=1, b=2)) == {'a': 1, 'b': 2}
    assert dumper(acc_schema.dummy(a=1, b=2, c=3)) == {'a': 1, 'b': 2}
    assert dumper(acc_schema.dummy(a=1, b=Skip())) == {'a': 1}
    assert dumper(acc_schema.dummy(a=1, b=Skip(), c=3)) == {'a': 1}

    assert dumper(acc_schema.dummy(a=Skip(), b=2)) == {'a': Skip(), 'b': 2}
    assert dumper(acc_schema.dummy(a=Skip(), b=2, c=3)) == {'a': Skip(), 'b': 2}
    assert dumper(acc_schema.dummy(a=Skip(), b=Skip())) == {'a': Skip()}
    assert dumper(acc_schema.dummy(a=Skip(), b=Skip(), c=3)) == {'a': Skip()}

    if is_required_a:
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy()),
            path=[acc_schema.path_elem_maker('a')] if debug_path else [],
        )
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy(b=1)),
            path=[acc_schema.path_elem_maker('a')] if debug_path else [],
        )

    if is_required_b:
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy(a=1)),
            path=[acc_schema.path_elem_maker('b')] if debug_path else [],
        )

    if not is_required_a:
        assert dumper(acc_schema.dummy(b=1)) == {'b': 1}
        assert dumper(acc_schema.dummy(b=Skip())) == {}

    if not is_required_b:
        assert dumper(acc_schema.dummy(a=1)) == {'a': 1}
        assert dumper(acc_schema.dummy(a=Skip())) == {'a': Skip()}

    if not is_required_a and not is_required_b:
        assert dumper(acc_schema.dummy()) == {}

    raises_path(
        SomeError(),
        lambda: dumper(acc_schema.dummy(a=SomeError(), b=Skip())),
        path=[acc_schema.path_elem_maker('a')] if debug_path else [],
    )

    raises_path(
        SomeError(),
        lambda: dumper(acc_schema.dummy(a=1, b=SomeError())),
        path=[acc_schema.path_elem_maker('b')] if debug_path else [],
    )

    raises_path(
        SomeError(0),
        lambda: dumper(acc_schema.dummy(a=SomeError(0), b=SomeError(1))),
        path=[acc_schema.path_elem_maker('a')] if debug_path else [],
    )


def test_wild_extra_targets(debug_ctx, debug_path, acc_schema):
    dumper_getter = make_dumper_getter(
        fig=figure(
            field('a', acc_schema.accessor_maker('a', is_required=True)),
        ),
        name_layout=OutputNameLayout(
            crown=OutDictCrown(
                {
                    'a': OutFieldCrown('a'),
                },
                sieves={}
            ),
            extra_move=ExtraTargets(('b',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )

    pytest.raises(ValueError, dumper_getter).match(
        full_match_regex_str("ExtraTargets ['b'] are attached to non-existing fields")
    )


@parametrize_bool('is_required_a', 'is_required_b')
def test_one_extra_target(debug_ctx, debug_path, is_required_a, is_required_b, acc_schema):
    dumper_getter = make_dumper_getter(
        fig=figure(
            field('a', acc_schema.accessor_maker('a', is_required=is_required_a)),
            field('b', acc_schema.accessor_maker('b', is_required=is_required_b)),
        ),
        name_layout=OutputNameLayout(
            crown=OutDictCrown(
                {
                    'a': OutFieldCrown('a'),
                },
                sieves={}
            ),
            extra_move=ExtraTargets(('b',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    dumper = dumper_getter()

    assert dumper(acc_schema.dummy(a=1, b={'e': 2})) == {'a': 1, 'e': 2}
    assert dumper(acc_schema.dummy(a=1, b={'b': 2})) == {'a': 1, 'b': 2}

    if is_required_a:
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy()),
            path=[acc_schema.path_elem_maker('a')] if debug_path else [],
        )
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy(b=1)),
            path=[acc_schema.path_elem_maker('a')] if debug_path else [],
        )

    if is_required_b:
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy(a=1)),
            path=[acc_schema.path_elem_maker('b')] if debug_path else [],
        )

    if not is_required_a:
        assert dumper(acc_schema.dummy(b={'f': 2})) == {'f': 2}

    if not is_required_b:
        assert dumper(acc_schema.dummy(a=1)) == {'a': 1}

    if not is_required_a and not is_required_b:
        assert dumper(acc_schema.dummy()) == {}

    raises_path(
        SomeError(),
        lambda: dumper(acc_schema.dummy(a=SomeError(), b=Skip())),
        path=[acc_schema.path_elem_maker('a')] if debug_path else [],
    )

    raises_path(
        SomeError(),
        lambda: dumper(acc_schema.dummy(a=1, b=SomeError())),
        path=[acc_schema.path_elem_maker('b')] if debug_path else [],
    )

    raises_path(
        SomeError(0),
        lambda: dumper(acc_schema.dummy(a=SomeError(0), b=SomeError(1))),
        path=[acc_schema.path_elem_maker('a')] if debug_path else [],
    )


@parametrize_bool('is_required_a', 'is_required_b', 'is_required_c', 'is_required_d')
def test_several_extra_target(
    debug_ctx, debug_path, is_required_a, is_required_b, is_required_c, is_required_d, acc_schema
):
    dumper_getter = make_dumper_getter(
        fig=figure(
            field('a', acc_schema.accessor_maker('a', is_required=is_required_a)),
            field('b', acc_schema.accessor_maker('b', is_required=is_required_b)),
            field('c', acc_schema.accessor_maker('c', is_required=is_required_c)),
            field('d', acc_schema.accessor_maker('d', is_required=is_required_d)),
        ),
        name_layout=OutputNameLayout(
            crown=OutDictCrown(
                {
                    'a': OutFieldCrown('a'),
                },
                sieves={},
            ),
            extra_move=ExtraTargets(('b', 'c', 'd')),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    dumper = dumper_getter()

    assert (
        dumper(acc_schema.dummy(a=1, b={'b1': 2}, c={'c1': 3}, d={'d1': 4}))
        ==
        {'a': 1, 'b1': 2, 'c1': 3, 'd1': 4}
    )
    assert (
        dumper(acc_schema.dummy(a=1, b={'b1': 2, 'b2': 3}, c={'c1': 4, 'c2': 5}, d={'d1': 6, 'd2': 7}))
        ==
        {'a': 1, 'b1': 2, 'b2': 3, 'c1': 4, 'c2': 5, 'd1': 6, 'd2': 7}
    )
    assert dumper(acc_schema.dummy(a=1, b={'d': 2}, c={'e': 3}, d={})) == {'a': 1, 'd': 2, 'e': 3}

    assert (
        dumper(acc_schema.dummy(a=1, b={'b1': 2, 'b2': 3}, c={'c1': 4, 'b2': 5}, d={}))
        ==
        {'a': 1, 'b1': 2, 'c1': 4, 'b2': 5}
    )

    if is_required_b:
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy(a=1, c={'c1': 2})),
            path=[acc_schema.path_elem_maker('b')] if debug_path else [],
        )
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy(a=1)),
            path=[acc_schema.path_elem_maker('b')] if debug_path else [],
        )

    if is_required_c:
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy(a=1, b={'b1': 2})),
            path=[acc_schema.path_elem_maker('c')] if debug_path else [],
        )

    if is_required_c and not is_required_b:
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy(a=1)),
            path=[acc_schema.path_elem_maker('c')] if debug_path else [],
        )

    requirement = {
        'b': is_required_b,
        'c': is_required_c,
        'd': is_required_d,
    }

    assert (
        dumper(acc_schema.dummy(a=1, **{k: {k: 1} for k, v in requirement.items() if v}))
        ==
        {'a': 1, **{k: 1 for k, v in requirement.items() if v}}
    )


def my_extractor(obj):
    try:
        return int_dumper(obj.b)
    except AttributeError:
        try:
            return int_dumper(obj['b'])
        except KeyError:
            return {}


@parametrize_bool('is_required_a')
def test_extra_extract(debug_ctx, debug_path, is_required_a, acc_schema):
    dumper_getter = make_dumper_getter(
        fig=figure(
            field('a', acc_schema.accessor_maker('a', is_required=is_required_a)),
            field('b', acc_schema.accessor_maker('b', is_required=True)),
        ),
        name_layout=OutputNameLayout(
            crown=OutDictCrown(
                {
                    'a': OutFieldCrown('a'),
                },
                sieves={}
            ),
            extra_move=ExtraExtract(my_extractor),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    dumper = dumper_getter()

    assert dumper(acc_schema.dummy(a=1, b={'e': 2})) == {'a': 1, 'e': 2}
    assert dumper(acc_schema.dummy(a=1, b={'b': 2})) == {'a': 1, 'b': 2}

    if not is_required_a:
        assert dumper(acc_schema.dummy(b={'f': 2})) == {'f': 2}
        assert dumper(acc_schema.dummy()) == {}

    assert dumper(acc_schema.dummy(a=1)) == {'a': 1}

    if is_required_a:
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy()),
            path=[acc_schema.path_elem_maker('a')] if debug_path else [],
        )
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy(b=1)),
            path=[acc_schema.path_elem_maker('a')] if debug_path else [],
        )

    raises_path(
        SomeError(),
        lambda: dumper(acc_schema.dummy(a=1, b=SomeError())),
        path=[],
    )

    raises_path(
        SomeError(0),
        lambda: dumper(acc_schema.dummy(a=SomeError(0), b=SomeError(1))),
        path=[acc_schema.path_elem_maker('a')] if debug_path else [],
    )


def test_optional_fields_at_list(debug_ctx, debug_path, acc_schema):
    dumper_getter = make_dumper_getter(
        fig=figure(
            field('a', acc_schema.accessor_maker('a', is_required=True)),
            field('b', acc_schema.accessor_maker('b', is_required=False)),
        ),
        name_layout=OutputNameLayout(
            crown=OutListCrown(
                [
                    OutFieldCrown('a'),
                    OutFieldCrown('b'),
                ],
            ),
            extra_move=None,
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )

    pytest.raises(ValueError, dumper_getter).match(
        full_match_regex_str("Optional fields ['b'] are found at list crown")
    )


@dataclass
class FlatMap:
    field: str
    mapped: str


@parametrize_bool('is_required_a', 'is_required_b')
@pytest.mark.parametrize(
    'mp', [
        SimpleNamespace(a=FlatMap('a', 'a'), b=FlatMap('b', 'b')),
        SimpleNamespace(a=FlatMap('a', 'm_a'), b=FlatMap('b', 'm_b')),
    ],
    ids=['as_is', 'diff']
)
def test_flat_mapping(debug_ctx, debug_path, is_required_a, is_required_b, acc_schema, mp):
    dumper_getter = make_dumper_getter(
        fig=figure(
            field(mp.a.field, acc_schema.accessor_maker('a', is_required_a)),
            field(mp.b.field, acc_schema.accessor_maker('b', is_required_b)),
        ),
        name_layout=OutputNameLayout(
            crown=OutDictCrown(
                {
                    mp.a.mapped: OutFieldCrown(mp.a.field),
                    mp.b.mapped: OutFieldCrown(mp.b.field),
                },
                sieves={
                    mp.b.mapped: skipper,
                },
            ),
            extra_move=None,
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )

    dumper = dumper_getter()

    assert dumper(acc_schema.dummy(a=1, b=2)) == {mp.a.mapped: 1, mp.b.mapped: 2}
    assert dumper(acc_schema.dummy(a=1, b=2, c=3)) == {mp.a.mapped: 1, mp.b.mapped: 2}
    assert dumper(acc_schema.dummy(a=1, b=Skip())) == {mp.a.mapped: 1}
    assert dumper(acc_schema.dummy(a=1, b=Skip(), c=3)) == {mp.a.mapped: 1}

    assert dumper(acc_schema.dummy(a=Skip(), b=2)) == {mp.a.mapped: Skip(), mp.b.mapped: 2}
    assert dumper(acc_schema.dummy(a=Skip(), b=2, c=3)) == {mp.a.mapped: Skip(), mp.b.mapped: 2}
    assert dumper(acc_schema.dummy(a=Skip(), b=Skip())) == {mp.a.mapped: Skip()}
    assert dumper(acc_schema.dummy(a=Skip(), b=Skip(), c=3)) == {mp.a.mapped: Skip()}

    if is_required_a:
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy()),
            path=[acc_schema.path_elem_maker(mp.a.field)] if debug_path else [],
        )
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy(b=1)),
            path=[acc_schema.path_elem_maker(mp.a.field)] if debug_path else [],
        )

    if is_required_b:
        raises_path(
            acc_schema.access_error,
            lambda: dumper(acc_schema.dummy(a=1)),
            path=[acc_schema.path_elem_maker(mp.b.field)] if debug_path else [],
        )

    if not is_required_a:
        assert dumper(acc_schema.dummy(b=1)) == {mp.b.mapped: 1}
        assert dumper(acc_schema.dummy(b=Skip())) == {}

    if not is_required_b:
        assert dumper(acc_schema.dummy(a=1)) == {mp.a.mapped: 1}
        assert dumper(acc_schema.dummy(a=Skip())) == {mp.a.mapped: Skip()}

    if not is_required_a and not is_required_b:
        assert dumper(acc_schema.dummy()) == {}

    raises_path(
        SomeError(),
        lambda: dumper(acc_schema.dummy(a=SomeError(), b=Skip())),
        path=[acc_schema.path_elem_maker(mp.a.field)] if debug_path else [],
    )

    raises_path(
        SomeError(),
        lambda: dumper(acc_schema.dummy(a=1, b=SomeError())),
        path=[acc_schema.path_elem_maker(mp.b.field)] if debug_path else [],
    )

    raises_path(
        SomeError(0),
        lambda: dumper(acc_schema.dummy(a=SomeError(0), b=SomeError(1))),
        path=[acc_schema.path_elem_maker(mp.a.field)] if debug_path else [],
    )


def test_direct_list(debug_ctx, debug_path, acc_schema):
    dumper_getter = make_dumper_getter(
        fig=figure(
            field('a', acc_schema.accessor_maker('a', True)),
            field('b', acc_schema.accessor_maker('b', True)),
        ),
        name_layout=OutputNameLayout(
            crown=OutListCrown(
                [
                    OutFieldCrown('a'),
                    OutFieldCrown('b'),
                ],
            ),
            extra_move=None,
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )

    dumper = dumper_getter()
    assert dumper(acc_schema.dummy(a=1, b=2)) == [1, 2]

    raises_path(
        SomeError(1),
        lambda: dumper(acc_schema.dummy(a=SomeError(1), b=2)),
        path=[acc_schema.path_elem_maker('a')] if debug_path else [],
    )

    raises_path(
        SomeError(1),
        lambda: dumper(acc_schema.dummy(a=SomeError(1), b=SomeError(2))),
        path=[acc_schema.path_elem_maker('a')] if debug_path else [],
    )

    raises_path(
        SomeError(2),
        lambda: dumper(acc_schema.dummy(a=1, b=SomeError(2))),
        path=[acc_schema.path_elem_maker('b')] if debug_path else [],
    )


def dict_skipper(data):
    return Skip() not in data.values()


def list_skipper(data):
    return Skip() not in data


def test_structure_flattening(debug_ctx, debug_path, acc_schema):
    dumper_getter = make_dumper_getter(
        fig=figure(
            field('a', acc_schema.accessor_maker('a', True)),
            field('b', acc_schema.accessor_maker('b', True)),
            field('c', acc_schema.accessor_maker('c', True)),
            field('d', acc_schema.accessor_maker('d', True)),
            field('e', acc_schema.accessor_maker('e', True)),
            field('f', acc_schema.accessor_maker('f', True)),
            field('g', acc_schema.accessor_maker('g', True)),
            field('h', acc_schema.accessor_maker('h', True)),
            field('extra', acc_schema.accessor_maker('extra', True)),
        ),
        name_layout=OutputNameLayout(
            crown=OutDictCrown(
                {
                    'z': OutDictCrown(
                        {
                            'y': OutFieldCrown('a'),
                            'x': OutFieldCrown('b'),
                        },
                        sieves={},
                    ),
                    'w': OutFieldCrown('c'),
                    'v': OutListCrown(
                        [
                            OutFieldCrown('d'),
                            OutDictCrown(
                                {
                                    'u': OutFieldCrown('e'),
                                },
                                sieves={},
                            ),
                            OutListCrown(
                                [
                                    OutFieldCrown('f')
                                ],
                            )
                        ],
                    ),
                    't': OutDictCrown(
                        {
                            's': OutFieldCrown('g'),
                        },
                        sieves={}
                    ),
                    'r': OutListCrown(
                        [
                            OutFieldCrown('h')
                        ]
                    )
                },
                sieves={
                    't': dict_skipper,
                    'r': list_skipper,
                },
            ),
            extra_move=ExtraTargets(('extra',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    dumper = dumper_getter()

    assert dumper(
        acc_schema.dummy(a=1, b=2, c=3, d=4, e=5, f=6, g=7, h=8, extra={})
    ) == {
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
        't': {
            's': 7
        },
        'r': [
            8
        ],
    }

    assert dumper(
        acc_schema.dummy(a=1, b=2, c=3, d=4, e=5, f=6, g=7, h=8, extra={'i': 9})
    ) == {
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
        't': {
            's': 7
        },
        'r': [
            8
        ],
        'i': 9,
    }

    assert dumper(
        acc_schema.dummy(a=1, b=2, c=3, d=4, e=5, f=6, g=7, h=Skip(), extra={})
    ) == {
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
        't': {
            's': 7
        },
    }

    assert dumper(
        acc_schema.dummy(a=1, b=2, c=3, d=4, e=5, f=6, g=Skip(), h=8, extra={})
    ) == {
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
        'r': [
            8
        ],
    }

    assert dumper(
        acc_schema.dummy(a=1, b=2, c=3, d=4, e=5, f=6, g=Skip(), h=Skip(), extra={})
    ) == {
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

    assert dumper(
        acc_schema.dummy(a=1, b=2, c=3, d=4, e=5, f=6, g=Skip(), h=Skip(), extra={'v': 'foo'})
    ) == {
        'z': {
            'y': 1,
            'x': 2,
        },
        'w': 3,
        'v': 'foo',  # sorry, merging is not implemented
    }

    raises_path(
        SomeError(5),
        lambda: dumper(acc_schema.dummy(a=1, b=2, c=3, d=4, e=SomeError(5), f=6, g=Skip(), h=Skip(), extra={})),
        path=[acc_schema.path_elem_maker('e')] if debug_path else [],
    )


@parametrize_bool('is_required_a', 'is_required_b')
def test_extra_target_at_crown(debug_ctx, debug_path, acc_schema, is_required_a, is_required_b):
    dumper_getter = make_dumper_getter(
        fig=figure(
            field('a', acc_schema.accessor_maker('a', is_required_a)),
            field('b', acc_schema.accessor_maker('b', is_required_b)),
        ),
        name_layout=OutputNameLayout(
            crown=OutDictCrown(
                {
                    'm_a': OutFieldCrown('a'),
                    'm_b': OutFieldCrown('b'),
                },
                sieves={},
            ),
            extra_move=ExtraTargets(('b',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, dumper_getter).match(
        full_match_regex_str("Extra targets ['b'] are found at crown")
    )

    dumper_getter = make_dumper_getter(
        fig=figure(
            field('a', acc_schema.accessor_maker('a', is_required_a)),
            field('b', acc_schema.accessor_maker('b', is_required_b)),
        ),
        name_layout=OutputNameLayout(
            crown=OutDictCrown(
                {
                    'm_a': OutFieldCrown('a'),
                    'm_b': OutFieldCrown('b'),
                },
                sieves={},
            ),
            extra_move=ExtraTargets(('b',)),
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    pytest.raises(ValueError, dumper_getter).match(
        full_match_regex_str("Extra targets ['b'] are found at crown")
    )


@dataclass
class SomeClass:
    value: int


@parametrize_bool('is_required_a')
def test_none_crown_at_dict_crown(debug_ctx, debug_path, acc_schema, is_required_a):
    dumper_getter = make_dumper_getter(
        fig=figure(
            field('a', acc_schema.accessor_maker('a', is_required_a)),
        ),
        name_layout=OutputNameLayout(
            crown=OutDictCrown(
                {
                    'w': OutNoneCrown(filler=DefaultValue(None)),
                    'x': OutNoneCrown(filler=DefaultValue(SomeClass(2))),
                    'y': OutFieldCrown('a'),
                    'z': OutNoneCrown(filler=DefaultFactory(list)),
                },
                sieves={},
            ),
            extra_move=None,
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    dumper = dumper_getter()

    assert dumper(acc_schema.dummy(a=1)) == {'w': None, 'x': SomeClass(2), 'y': 1, 'z': []}


def test_none_crown_at_list_crown(debug_ctx, debug_path, acc_schema):
    dumper_getter = make_dumper_getter(
        fig=figure(
            field('a', acc_schema.accessor_maker('a', True)),
        ),
        name_layout=OutputNameLayout(
            crown=OutListCrown(
                [
                    OutNoneCrown(filler=DefaultValue(None)),
                    OutNoneCrown(filler=DefaultValue(SomeClass(2))),
                    OutFieldCrown('a'),
                    OutNoneCrown(filler=DefaultFactory(list)),
                ],
            ),
            extra_move=None,
        ),
        debug_path=debug_path,
        debug_ctx=debug_ctx,
    )
    dumper = dumper_getter()

    assert dumper(acc_schema.dummy(a=1)) == [None, SomeClass(2), 1, []]
