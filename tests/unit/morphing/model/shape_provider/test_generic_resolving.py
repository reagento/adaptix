from typing import Any, Dict, Generic, List, Tuple, TypeVar

import pytest
from pytest import param
from tests_helpers import ModelSpec, cond_list, exclude_model_spec, load_namespace_keeping_module, requires

from adaptix import CannotProvide, Retort
from adaptix._internal.feature_requirement import (
    HAS_PY_39,
    HAS_PY_310,
    HAS_PY_311,
    HAS_PY_312,
    HAS_SELF_TYPE,
    HAS_STD_CLASSES_GENERICS,
    HAS_TV_TUPLE,
    IS_PYPY,
)
from adaptix._internal.provider.request_cls import LocMap, LocStack, TypeHintLoc
from adaptix._internal.provider.shape_provider import (
    InputShapeRequest,
    OutputShapeRequest,
    provide_generic_resolved_shape,
)

from .local_helpers import assert_fields_types

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

# this models can be generics only after Python 3.11
adaptix_model_spec_requirements = {
    ModelSpec.TYPED_DICT: HAS_PY_311,
    ModelSpec.NAMED_TUPLE: HAS_PY_311,
}


@pytest.fixture(
    params=[
        pytest.param('data_gen_models.py', id='inheritance'),
        *cond_list(
            HAS_PY_312,
            [pytest.param('data_gen_models_312.py', id='syntax_sugar')],
        ),
    ]
)
def gen_models_ns(model_spec, request):
    # need to pass tests at 3.9
    with load_namespace_keeping_module(request.param, vars={'model_spec': model_spec}) as ns:
        yield ns


def test_no_generic(model_spec):
    @model_spec.decorator
    class Simple(*model_spec.bases):
        a: int
        b: str

    assert_fields_types(Simple, {'a': int, 'b': str})


def test_type_var_field(gen_models_ns):
    WithTVField = gen_models_ns.WithTVField

    assert_fields_types(WithTVField, {'a': int, 'b': Any})
    assert_fields_types(WithTVField[str], {'a': int, 'b': str})
    assert_fields_types(WithTVField[T], {'a': int, 'b': T})


@pytest.mark.parametrize('tp', [List, list] if HAS_STD_CLASSES_GENERICS else [List])
def test_gen_field(model_spec, tp):
    @model_spec.decorator
    class WithGenField(*model_spec.bases, Generic[T]):
        a: int
        b: tp[T]

    assert_fields_types(WithGenField, {'a': int, 'b': tp[Any]})
    assert_fields_types(WithGenField[str], {'a': int, 'b': tp[str]})
    assert_fields_types(WithGenField[T], {'a': int, 'b': tp[T]})


@pytest.mark.parametrize('tp1', [List, list] if HAS_STD_CLASSES_GENERICS else [List])
@pytest.mark.parametrize('tp2', [Dict, dict] if HAS_STD_CLASSES_GENERICS else [Dict])
def test_two_params(model_spec, tp1, tp2):
    @model_spec.decorator
    class WithStdGenField(*model_spec.bases, Generic[K, V]):
        a: int
        b: tp1[K]
        c: tp2[K, V]

    assert_fields_types(
        WithStdGenField,
        {'a': int, 'b': tp1[Any], 'c': tp2[Any, Any]},
    )
    assert_fields_types(
        WithStdGenField[str, int],
        {'a': int, 'b': tp1[str], 'c': tp2[str, int]},
    )
    assert_fields_types(
        WithStdGenField[K, V],
        {'a': int, 'b': tp1[K], 'c': tp2[K, V]},
    )


def test_sub_generic(model_spec):
    @model_spec.decorator
    class SubGen(*model_spec.bases, Generic[T]):
        foo: T

    @model_spec.decorator
    class WithSubUnparametrized(*model_spec.bases, Generic[T]):
        a: int
        b: T
        c: SubGen  # test that we differ SubGen and SubGen[T]

    assert_fields_types(
        WithSubUnparametrized,
        {'a': int, 'b': Any, 'c': SubGen},
    )
    assert_fields_types(
        WithSubUnparametrized[str],
        {'a': int, 'b': str, 'c': SubGen},
    )
    assert_fields_types(
        WithSubUnparametrized[K],
        {'a': int, 'b': K, 'c': SubGen},
    )


@exclude_model_spec(ModelSpec.NAMED_TUPLE)
def test_single_inheritance(model_spec):
    @model_spec.decorator
    class Parent(*model_spec.bases, Generic[T]):
        a: T

    @model_spec.decorator
    class Child(Parent[int]):
        b: str

    assert_fields_types(
        Child,
        {'a': int, 'b': str},
    )


@exclude_model_spec(ModelSpec.NAMED_TUPLE)
def test_single_inheritance_generic_child(model_spec):
    @model_spec.decorator
    class Parent(*model_spec.bases, Generic[T]):
        a: T

    @model_spec.decorator
    class Child(Parent[int], Generic[T]):
        b: str
        c: T

    assert_fields_types(
        Child[bool],
        {'a': int, 'b': str, 'c': bool},
    )
    assert_fields_types(
        Child,
        {'a': int, 'b': str, 'c': Any},
    )
    assert_fields_types(
        Child[T],
        {'a': int, 'b': str, 'c': T},
    )


@exclude_model_spec(ModelSpec.NAMED_TUPLE, ModelSpec.ATTRS)
def test_multiple_inheritance(model_spec):
    @model_spec.decorator
    class Parent1(*model_spec.bases, Generic[T]):
        a: T

    @model_spec.decorator
    class Parent2(*model_spec.bases, Generic[T]):
        b: T

    @model_spec.decorator
    class Child(Parent1[int], Parent2[bool], Generic[T]):
        b: str
        c: T

    assert_fields_types(
        Child[bool],
        {'a': int, 'b': str, 'c': bool},
    )
    assert_fields_types(
        Child[T],
        {'a': int, 'b': str, 'c': T},
    )
    assert_fields_types(
        Child,
        {'a': int, 'b': str, 'c': Any},
    )


T1 = TypeVar('T1')
T2 = TypeVar('T2')
T3 = TypeVar('T3')
T4 = TypeVar('T4')
T5 = TypeVar('T5')
T6 = TypeVar('T6')
T7 = TypeVar('T7')


@exclude_model_spec(ModelSpec.NAMED_TUPLE, ModelSpec.ATTRS)
@pytest.mark.parametrize('tp', [List, list] if HAS_STD_CLASSES_GENERICS else [List])
def test_generic_multiple_inheritance(model_spec, tp) -> None:
    @model_spec.decorator
    class GrandParent(*model_spec.bases, Generic[T1, T2]):
        a: T1
        b: tp[T2]

    @model_spec.decorator
    class Parent1(GrandParent[int, T3], Generic[T3, T4]):
        c: T4

    @model_spec.decorator
    class Parent2(GrandParent[int, T5], Generic[T5, T6]):
        d: T6

    @model_spec.decorator
    class Child(Parent1[int, bool], Parent2[str, bytes], Generic[T7]):
        e: T7

    assert_fields_types(
        Child,
        {'a': int, 'b': tp[int], 'c': bool, 'd': bytes, 'e': Any},
    )
    assert_fields_types(
        Child[complex],
        {'a': int, 'b': tp[int], 'c': bool, 'd': bytes, 'e': complex},
    )
    assert_fields_types(
        Child[T],
        {'a': int, 'b': tp[int], 'c': bool, 'd': bytes, 'e': T},
    )


# TODO: fix it
skip_if_pypy_39_or_310 = pytest.mark.skipif(
    IS_PYPY and (HAS_PY_39 or HAS_PY_310),
    reason='At this python version and implementation list has __init__ that allow to generate Shape',
)


@pytest.mark.parametrize(
    'tp',
    [
        int,
        param(list, id='list', marks=skip_if_pypy_39_or_310),
        param(List, id='List', marks=skip_if_pypy_39_or_310),
        param(List[T], id='List[T]', marks=skip_if_pypy_39_or_310),
        param(List[int], id='List[int]', marks=skip_if_pypy_39_or_310),
    ] + (
        [param(list[T], id='list[T]', marks=skip_if_pypy_39_or_310)]
        if HAS_STD_CLASSES_GENERICS else
        []
    )
)
def test_not_a_model(tp):
    retort = Retort()
    mediator = retort._create_mediator()

    with pytest.raises(CannotProvide):
        provide_generic_resolved_shape(
            mediator,
            InputShapeRequest(loc_stack=LocStack(LocMap(TypeHintLoc(type=tp)))),
        )

    with pytest.raises(CannotProvide):
        provide_generic_resolved_shape(
            mediator,
            OutputShapeRequest(loc_stack=LocStack(LocMap(TypeHintLoc(type=tp)))),
        )


@exclude_model_spec(ModelSpec.NAMED_TUPLE, ModelSpec.ATTRS)
def test_generic_mixed_inheritance(model_spec):
    @model_spec.decorator
    class Parent1(*model_spec.bases):
        a: int

    @model_spec.decorator
    class Parent2(*model_spec.bases, Generic[T]):
        b: T

    @model_spec.decorator
    class Child12(Parent1, Parent2[str]):
        c: bool

    assert_fields_types(
        Child12,
        {'a': int, 'b': str, 'c': bool},
    )

    @model_spec.decorator
    class Child21(Parent2[str], Parent1):
        c: bool

    assert_fields_types(
        Child21,
        {'b': str, 'a': int, 'c': bool},
    )


@exclude_model_spec(ModelSpec.NAMED_TUPLE)
def test_generic_parents_with_type_override(model_spec):
    @model_spec.decorator
    class Parent(*model_spec.bases, Generic[T]):
        a: T

    @model_spec.decorator
    class Child(Parent[int]):
        a: bool

    assert_fields_types(
        Child,
        {'a': bool},
    )


@exclude_model_spec(ModelSpec.NAMED_TUPLE)
def test_generic_parents_with_type_override_generic(model_spec):
    @model_spec.decorator
    class Parent(*model_spec.bases, Generic[T]):
        a: T

    @model_spec.decorator
    class Child(Parent[int], Generic[T]):
        a: bool
        b: T

    assert_fields_types(
        Child,
        {'a': bool, 'b': Any},
    )
    assert_fields_types(
        Child[T],
        {'a': bool, 'b': T},
    )
    assert_fields_types(
        Child[str],
        {'a': bool, 'b': str},
    )


@requires(HAS_SELF_TYPE)
def test_self_type(model_spec):
    from typing import Self

    @model_spec.decorator
    class WithSelf(*model_spec.bases):
        a: Self

    assert_fields_types(
        WithSelf,
        {'a': Self},
    )


@requires(HAS_TV_TUPLE)
def test_type_var_tuple_begin(model_spec, gen_models_ns):
    from typing import Unpack

    WithTVTupleBegin = gen_models_ns.WithTVTupleBegin

    assert_fields_types(
        WithTVTupleBegin,
        {
            'a': Tuple[Unpack[Tuple[Any, ...]]],
            'b': Any,
        },
    )
    assert_fields_types(
        WithTVTupleBegin[int, str],
        {
            'a': Tuple[int],
            'b': str,
        },
    )
    assert_fields_types(
        WithTVTupleBegin[int, str, bool],
        {
            'a': Tuple[int, str],
            'b': bool,
        },
    )
    assert_fields_types(
        WithTVTupleBegin[int, Unpack[Tuple[str, bool]]],
        {
            'a': Tuple[int, str],
            'b': bool,
        },
    )
    assert_fields_types(
        WithTVTupleBegin[Unpack[Tuple[str, bool]], Unpack[Tuple[str, bool]]],
        {
            'a': Tuple[str, bool, str],
            'b': bool,
        },
    )


@requires(HAS_TV_TUPLE)
def test_type_var_tuple_end(model_spec, gen_models_ns):
    from typing import Unpack

    WithTVTupleEnd = gen_models_ns.WithTVTupleEnd

    assert_fields_types(
        WithTVTupleEnd,
        {
            'a': Any,
            'b': Tuple[Unpack[Tuple[Any, ...]]],
        },
    )
    assert_fields_types(
        WithTVTupleEnd[int, str],
        {
            'a': int,
            'b': Tuple[str],
        },
    )
    assert_fields_types(
        WithTVTupleEnd[int, str, bool],
        {
            'a': int,
            'b': Tuple[str, bool],
        },
    )
    assert_fields_types(
        WithTVTupleEnd[int, Unpack[Tuple[str, bool]]],
        {
            'a': int,
            'b': Tuple[str, bool],
        },
    )
    assert_fields_types(
        WithTVTupleEnd[Unpack[Tuple[str, bool]], Unpack[Tuple[str, bool]]],
        {
            'a': str,
            'b': Tuple[bool, str, bool],
        },
    )


@requires(HAS_TV_TUPLE)
def test_type_var_tuple_middle(model_spec, gen_models_ns):
    from typing import Unpack

    WithTVTupleMiddle = gen_models_ns.WithTVTupleMiddle

    assert_fields_types(
        WithTVTupleMiddle,
        {
            'a': Any,
            'b': Tuple[Unpack[Tuple[Any, ...]]],
            'c': Any,
        },
    )
    assert_fields_types(
        WithTVTupleMiddle[int, str],
        {
            'a': int,
            'b': Tuple[()],
            'c': str,
        },
    )
    assert_fields_types(
        WithTVTupleMiddle[int, str, bool],
        {
            'a': int,
            'b': Tuple[str],
            'c': bool
        },
    )
    assert_fields_types(
        WithTVTupleMiddle[int, str, str, bool],
        {
            'a': int,
            'b': Tuple[str, str],
            'c': bool
        },
    )
    assert_fields_types(
        WithTVTupleMiddle[int, Unpack[Tuple[str, bool]]],
        {
            'a': int,
            'b': Tuple[str],
            'c': bool
        },
    )
    assert_fields_types(
        WithTVTupleMiddle[int, Unpack[Tuple[str, bool]], int],
        {
            'a': int,
            'b': Tuple[str, bool],
            'c': int
        },
    )
    assert_fields_types(
        WithTVTupleMiddle[int, Unpack[Tuple[str, ...]], int],
        {
            'a': int,
            'b': Tuple[Unpack[Tuple[str, ...]]],
            'c': int
        },
    )
    assert_fields_types(
        WithTVTupleMiddle[int, bool, Unpack[Tuple[str, ...]], int],
        {
            'a': int,
            'b': Tuple[bool, Unpack[Tuple[str, ...]]],
            'c': int
        },
    )
