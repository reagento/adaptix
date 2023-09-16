from dataclasses import dataclass
from types import FunctionType
from typing import Any, Dict, Optional, Union

import pytest
from tests_helpers import TestRetort, full_match_regex_str, type_of

from adaptix import DebugTrail, NameStyle, Provider, bound, name_mapping
from adaptix._internal.model_tools.definitions import (
    BaseField,
    BaseShape,
    Default,
    DefaultFactory,
    DefaultValue,
    InputField,
    InputShape,
    NoDefault,
    OutputField,
    OutputShape,
    Param,
    ParamKind,
    ParamKwargs,
    create_attr_accessor,
)
from adaptix._internal.provider.model.basic_gen import NameSanitizer
from adaptix._internal.provider.model.crown_definitions import (
    ExtraCollect,
    ExtraExtract,
    ExtraForbid,
    ExtraKwargs,
    ExtraSaturate,
    ExtraSkip,
    ExtraTargets,
    InpDictCrown,
    InpFieldCrown,
    InpListCrown,
    InpNoneCrown,
    InputNameLayout,
    InputNameLayoutRequest,
    OutDictCrown,
    OutFieldCrown,
    OutListCrown,
    OutNoneCrown,
    OutputNameLayout,
    OutputNameLayoutRequest,
)
from adaptix._internal.provider.model.definitions import InputShapeRequest, OutputShapeRequest
from adaptix._internal.provider.model.dumper_provider import (
    BuiltinOutputCreationMaker,
    ModelDumperProvider,
    make_output_extraction,
)
from adaptix._internal.provider.model.loader_provider import (
    BuiltinInputExtractionMaker,
    ModelLoaderProvider,
    make_input_creation,
)
from adaptix._internal.provider.name_layout.component import (
    BuiltinExtraMoveAndPoliciesMaker,
    BuiltinSievesMaker,
    BuiltinStructureMaker,
)
from adaptix._internal.provider.name_layout.provider import BuiltinNameLayoutProvider
from adaptix._internal.provider.provider_template import ValueProvider
from adaptix._internal.provider.request_cls import DumperRequest, FieldLoc, LoaderRequest, LocMap, TypeHintLoc
from adaptix._internal.provider.request_filtering import AnyRequestChecker


@dataclass
class TestField:
    id: str
    is_required: bool = True
    default: Default = NoDefault()


@dataclass
class Layouts:
    inp: InputNameLayout
    out: OutputNameLayout


def stub(*args, **kwargs):
    pass


def make_layouts(
    *fields_or_providers: Union[TestField, Provider],
    loc_map: LocMap = LocMap(),
) -> Layouts:
    fields = [element for element in fields_or_providers if isinstance(element, TestField)]
    providers = [element for element in fields_or_providers if isinstance(element, Provider)]
    input_shape = InputShape(
        fields=tuple(
            InputField(
                id=fld.id,
                type=Any,
                default=fld.default,
                metadata={},
                is_required=fld.is_required,
                original=None,
            )
            for fld in fields
        ),
        params=tuple(
            Param(
                field_id=fld.id,
                name=fld.id,
                kind=ParamKind.POS_OR_KW,
            )
            for fld in fields
        ),
        constructor=stub,
        kwargs=ParamKwargs(Any),
        overriden_types=frozenset(fld.id for fld in fields),
    )
    output_shape = OutputShape(
        fields=tuple(
            OutputField(
                id=fld.id,
                type=Any,
                default=fld.default,
                metadata={},
                accessor=create_attr_accessor(
                    attr_name=fld.id,
                    is_required=fld.is_required,
                ),
                original=None,
            )
            for fld in fields
        ),
        overriden_types=frozenset(fld.id for fld in fields),
    )
    retort = TestRetort(
        recipe=[
            *providers,
            BuiltinNameLayoutProvider(
                structure_maker=BuiltinStructureMaker(),
                sieves_maker=BuiltinSievesMaker(),
                extra_move_maker=BuiltinExtraMoveAndPoliciesMaker(),
                extra_policies_maker=BuiltinExtraMoveAndPoliciesMaker(),
            ),
            bound(Any, ValueProvider(DumperRequest, stub)),
            bound(Any, ValueProvider(LoaderRequest, stub)),
            ValueProvider(InputShapeRequest, input_shape),
            ValueProvider(OutputShapeRequest, output_shape),
            ModelLoaderProvider(NameSanitizer(), BuiltinInputExtractionMaker(), make_input_creation),
            ModelDumperProvider(NameSanitizer(), make_output_extraction, BuiltinOutputCreationMaker()),
        ]
    ).replace(
        strict_coercion=True,
        debug_trail=DebugTrail.ALL,
    )
    inp_request = InputNameLayoutRequest(
        loc_map=loc_map,
        shape=input_shape,
    )
    out_request = OutputNameLayoutRequest(
        loc_map=loc_map,
        shape=output_shape,
    )
    inp_name_layout = retort.provide(inp_request)
    out_name_layout = retort.provide(out_request)
    retort.provide(
        LoaderRequest(
            loc_map=loc_map,
        )
    )
    retort.provide(
        DumperRequest(
            loc_map=loc_map,
        )
    )
    return Layouts(inp_name_layout, out_name_layout)


DEFAULT_NAME_MAPPING = name_mapping(
    chain=None,
    skip=(),
    only=AnyRequestChecker(),
    map={},
    trim_trailing_underscore=True,
    name_style=None,
    as_list=False,
    omit_default=False,
    extra_in=ExtraSkip(),
    extra_out=ExtraSkip(),
)


def test_default_parameters():
    layouts = make_layouts(
        TestField('a'),
        TestField('b_'),
        TestField('c_', default=DefaultValue(0)),
        DEFAULT_NAME_MAPPING,
    )
    assert layouts == Layouts(
        InputNameLayout(
            crown=InpDictCrown(
                map={
                    'a': InpFieldCrown('a'),
                    'b': InpFieldCrown('b_'),
                    'c': InpFieldCrown('c_'),
                },
                extra_policy=ExtraSkip(),
            ),
            extra_move=None,
        ),
        OutputNameLayout(
            crown=OutDictCrown(
                map={
                    'a': OutFieldCrown('a'),
                    'b': OutFieldCrown('b_'),
                    'c': OutFieldCrown('c_'),
                },
                sieves={},
            ),
            extra_move=None,
        ),
    )


def assert_flat_name_mapping(
    provider: Provider,
    mapping: Dict[str, Optional[str]],
):
    layouts = make_layouts(
        *[
            TestField(field_name, is_required=False)
            for field_name in mapping.keys()
        ],
        provider,
        DEFAULT_NAME_MAPPING,
    )
    assert {
        crown.id: key  # type: ignore
        for key, crown in layouts.inp.crown.map.items()  # type: ignore
    } == {
        key: mapped_key
        for key, mapped_key in mapping.items()
        if mapped_key is not None
    }


def test_name_mutating():
    assert_flat_name_mapping(
        name_mapping(
            map={},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {
            'a': 'A',
            'b': 'B',
            'c_': 'C',
            'd__': 'D__',
        },
    )
    assert_flat_name_mapping(
        name_mapping(
            map={},
            trim_trailing_underscore=False,
            name_style=NameStyle.UPPER,
        ),
        {
            'a': 'A',
            'b': 'B',
            'c_': 'C_',
            'd__': 'D__',
        },
    )
    assert_flat_name_mapping(
        name_mapping(
            map={'a': 'z'},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {
            'a': 'z',
            'b': 'B',
            'c_': 'C',
            'd__': 'D__',
        },
    )
    assert_flat_name_mapping(
        name_mapping(
            map={'a': 'z', 'c_': 'y'},
            trim_trailing_underscore=True,
            name_style=NameStyle.UPPER,
        ),
        {
            'a': 'z',
            'b': 'B',
            'c_': 'y',
            'd__': 'D__',
        },
    )


def test_name_filtering():
    assert_flat_name_mapping(
        name_mapping(
            skip=['a', 'xxx'],
            only=AnyRequestChecker(),
            map={},
        ),
        {
            'a': None,
            'b': 'b',
            'c': 'c',
        },
    )
    assert_flat_name_mapping(
        name_mapping(
            skip=[],
            only=['a'],
            map={},
        ),
        {
            'a': 'a',
            'b': None,
            'c': None,
        },
    )
    assert_flat_name_mapping(
        name_mapping(
            skip=['b'],
            only=AnyRequestChecker(),
            map={},
        ),
        {
            'a': 'a',
            'b': None,
            'c': 'c',
        },
    )
    assert_flat_name_mapping(
        name_mapping(
            skip=['b'],
            only=['a', 'b'],
            map={},
        ),
        {
            'a': 'a',
            'b': None,
            'c': None,
        },
    )


def test_as_list():
    assert make_layouts(
        TestField('a'),
        TestField('b'),
        name_mapping(
            map={},
            as_list=True,
        ),
        DEFAULT_NAME_MAPPING,
    ) == Layouts(
        inp=InputNameLayout(
            crown=InpListCrown(
                map=[
                    InpFieldCrown(id='a'),
                    InpFieldCrown(id='b'),
                ],
                extra_policy=ExtraSkip()
            ),
            extra_move=None,
        ),
        out=OutputNameLayout(
            crown=OutListCrown(
                map=[
                    OutFieldCrown(id='a'),
                    OutFieldCrown(id='b')
                ]
            ),
            extra_move=None
        )
    )

    assert make_layouts(
        TestField('a'),
        TestField('b'),
        TestField('c'),
        name_mapping(
            map={
                'a': 1,
                'b': 0,
            },
            as_list=True,
        ),
        DEFAULT_NAME_MAPPING,
    ) == Layouts(
        inp=InputNameLayout(
            crown=InpListCrown(
                map=[
                    InpFieldCrown(id='b'),
                    InpFieldCrown(id='a'),
                    InpFieldCrown(id='c'),
                ],
                extra_policy=ExtraSkip()
            ),
            extra_move=None,
        ),
        out=OutputNameLayout(
            crown=OutListCrown(
                map=[
                    OutFieldCrown(id='b'),
                    OutFieldCrown(id='a'),
                    OutFieldCrown(id='c')
                ]
            ),
            extra_move=None
        )
    )


def test_map_via_pred():
    assert make_layouts(
        TestField('a'),
        TestField('b'),
        TestField('c'),
        name_mapping(
            map=[
                ('a|b', ('foo', ...))
            ],
        ),
        DEFAULT_NAME_MAPPING,
    ) == Layouts(
        inp=InputNameLayout(
            crown=InpDictCrown(
                map={
                    'foo': InpDictCrown(
                        map={
                            'a': InpFieldCrown('a'),
                            'b': InpFieldCrown('b'),
                        },
                        extra_policy=ExtraSkip(),
                    ),
                    'c': InpFieldCrown('c'),
                },
                extra_policy=ExtraSkip(),
            ),
            extra_move=None,
        ),
        out=OutputNameLayout(
            crown=OutDictCrown(
                map={
                    'foo': OutDictCrown(
                        map={
                            'a': OutFieldCrown('a'),
                            'b': OutFieldCrown('b'),
                        },
                        sieves={},
                    ),
                    'c': OutFieldCrown('c'),
                },
                sieves={},
            ),
            extra_move=None
        )
    )


def my_func_mapper(shape: BaseShape, field: BaseField):
    return '$' + field.id


def test_map_via_func():
    assert make_layouts(
        TestField('a'),
        TestField('b'),
        TestField('c'),
        name_mapping(
            map=[
                ('a|b', my_func_mapper)
            ],
        ),
        DEFAULT_NAME_MAPPING,
    ) == Layouts(
        inp=InputNameLayout(
            crown=InpDictCrown(
                map={
                    '$a': InpFieldCrown('a'),
                    '$b': InpFieldCrown('b'),
                    'c': InpFieldCrown('c'),
                },
                extra_policy=ExtraSkip(),
            ),
            extra_move=None,
        ),
        out=OutputNameLayout(
            crown=OutDictCrown(
                map={
                    '$a': OutFieldCrown('a'),
                    '$b': OutFieldCrown('b'),
                    'c': OutFieldCrown('c'),
                },
                sieves={},
            ),
            extra_move=None
        )
    )


def test_map_to_none():
    assert make_layouts(
        TestField('a', is_required=False),
        TestField('b', is_required=False),
        TestField('c', is_required=False),
        name_mapping(
            map={
                'b': None,
            },
        ),
        DEFAULT_NAME_MAPPING,
    ) == Layouts(
        inp=InputNameLayout(
            crown=InpDictCrown(
                map={
                    'a': InpFieldCrown('a'),
                    'c': InpFieldCrown('c'),
                },
                extra_policy=ExtraSkip(),
            ),
            extra_move=None,
        ),
        out=OutputNameLayout(
            crown=OutDictCrown(
                map={
                    'a': OutFieldCrown('a'),
                    'c': OutFieldCrown('c'),
                },
                sieves={},
            ),
            extra_move=None
        )
    )


def test_gaps_filling():
    assert make_layouts(
        TestField('a'),
        TestField('b'),
        name_mapping(
            map={
                'a': 0,
                'b': 2,
            },
        ),
        DEFAULT_NAME_MAPPING,
    ) == Layouts(
        inp=InputNameLayout(
            crown=InpListCrown(
                map=[
                    InpFieldCrown(id='a'),
                    InpNoneCrown(),
                    InpFieldCrown(id='b'),
                ],
                extra_policy=ExtraSkip()
            ),
            extra_move=None,
        ),
        out=OutputNameLayout(
            crown=OutListCrown(
                map=[
                    OutFieldCrown(id='a'),
                    OutNoneCrown(filler=DefaultValue(value=None)),
                    OutFieldCrown(id='b')
                ]
            ),
            extra_move=None
        )
    )


def test_structure_flattening():
    assert make_layouts(
        TestField('a'),
        TestField('b'),
        TestField('c'),
        TestField('d'),
        TestField('e'),
        TestField('f'),
        name_mapping(
            map={
                'a': ('x', 'y', 0),
                'b': ('x', 'y', 1),
                'c': ('x', 'z'),
                'd': ('w', 0),
                'e': ('x', ...),
            },
        ),
        DEFAULT_NAME_MAPPING,
    ) == Layouts(
        inp=InputNameLayout(
            crown=InpDictCrown(
                map={
                    'f': InpFieldCrown(id='f'),
                    'w': InpListCrown(
                        map=[
                            InpFieldCrown(id='d'),
                        ],
                        extra_policy=ExtraSkip(),
                    ),
                    'x': InpDictCrown(
                        map={
                            'e': InpFieldCrown(id='e'),
                            'y': InpListCrown(
                                map=[
                                    InpFieldCrown(id='a'),
                                    InpFieldCrown(id='b'),
                                ],
                                extra_policy=ExtraSkip(),
                            ),
                            'z': InpFieldCrown(id='c'),
                        },
                        extra_policy=ExtraSkip()
                    ),
                },
                extra_policy=ExtraSkip()
            ),
            extra_move=None
        ),
        out=OutputNameLayout(
            crown=OutDictCrown(
                map={
                    'f': OutFieldCrown(id='f'),
                    'w': OutListCrown(
                        map=[
                            OutFieldCrown(id='d'),
                        ]
                    ),
                    'x': OutDictCrown(
                        map={
                            'e': OutFieldCrown(id='e'),
                            'y': OutListCrown(
                                map=[
                                    OutFieldCrown(id='a'),
                                    OutFieldCrown(id='b'),
                                ]
                            ),
                            'z': OutFieldCrown(id='c')
                        },
                        sieves={}
                    )
                },
                sieves={}
            ),
            extra_move=None
        )
    )


def test_omit_default():
    layouts = make_layouts(
        TestField('a_', default=NoDefault()),
        TestField('b_', default=DefaultValue(0)),
        TestField('c_', default=DefaultFactory(list)),
        name_mapping(omit_default=True),
        DEFAULT_NAME_MAPPING,
    )
    assert layouts == Layouts(
        type_of(InputNameLayout),
        OutputNameLayout(
            crown=OutDictCrown(
                map={
                    'a': OutFieldCrown('a_'),
                    'b': OutFieldCrown('b_'),
                    'c': OutFieldCrown('c_'),
                },
                sieves={
                    'b': type_of(FunctionType),
                    'c': type_of(FunctionType),
                },
            ),
            extra_move=None,
        ),
    )

    layouts = make_layouts(
        TestField('a_', default=NoDefault()),
        TestField('b_', default=DefaultValue(0)),
        TestField('c_', default=DefaultFactory(list)),
        name_mapping(
            omit_default=False,
        ),
        DEFAULT_NAME_MAPPING,
    )
    assert layouts == Layouts(
        type_of(InputNameLayout),
        OutputNameLayout(
            crown=OutDictCrown(
                map={
                    'a': OutFieldCrown('a_'),
                    'b': OutFieldCrown('b_'),
                    'c': OutFieldCrown('c_'),
                },
                sieves={},
            ),
            extra_move=None,
        ),
    )


def my_saturator(obj, extra):
    pass


@pytest.mark.parametrize(
    ['extra_in', 'extra_policy', 'extra_move'],
    [
        (
            ExtraSkip(),
            ExtraSkip(),
            None,
        ),
        (
            ExtraForbid(),
            ExtraForbid(),
            None,
        ),
        (
            ExtraKwargs(),
            ExtraCollect(),
            ExtraKwargs(),
        ),
        (
            'a',
            ExtraCollect(),
            ExtraTargets(('a',)),
        ),
        (
            ['a'],
            ExtraCollect(),
            ExtraTargets(('a',)),
        ),
        (
            ('a',),
            ExtraCollect(),
            ExtraTargets(('a',)),
        ),
        (
            {'a'},
            ExtraCollect(),
            ExtraTargets(('a',)),
        ),
        (
            my_saturator,
            ExtraCollect(),
            ExtraSaturate(my_saturator),
        ),
    ]
)
def test_input_extra_dict(extra_in, extra_policy, extra_move):
    layouts = make_layouts(
        TestField('a'),
        name_mapping(
            extra_in=extra_in,
        ),
        DEFAULT_NAME_MAPPING,
    )
    assert layouts == Layouts(
        InputNameLayout(
            crown=InpDictCrown(
                map={} if isinstance(extra_move, ExtraTargets) else {'a': InpFieldCrown('a')},
                extra_policy=extra_policy,
            ),
            extra_move=extra_move,
        ),
        type_of(OutputNameLayout),
    )


def my_extractor(obj):
    pass


@pytest.mark.parametrize(
    ['extra_out', 'extra_move'],
    [
        (
            ExtraSkip(),
            None,
        ),
        (
            'a',
            ExtraTargets(('a',)),
        ),
        (
            ['a'],
            ExtraTargets(('a',)),
        ),
        (
            ('a',),
            ExtraTargets(('a',)),
        ),
        (
            {'a'},
            ExtraTargets(('a',)),
        ),
        (
            my_extractor,
            ExtraExtract(my_extractor),
        ),
    ]
)
def test_output_extra_dict(extra_out, extra_move):
    layouts = make_layouts(
        TestField('a'),
        name_mapping(
            extra_out=extra_out,
        ),
        DEFAULT_NAME_MAPPING,
    )
    assert layouts == Layouts(
        type_of(InputNameLayout),
        OutputNameLayout(
            crown=OutDictCrown(
                map={} if isinstance(extra_move, ExtraTargets) else {'a': OutFieldCrown('a')},
                sieves={},
            ),
            extra_move=extra_move,
        ),
    )


class Foo:
    pass


TYPE_HINT_LOC_MAP = LocMap(
    TypeHintLoc(
        type=Foo,
    ),
)
FIELD_LOC_MAP = TYPE_HINT_LOC_MAP.add(
    FieldLoc(
        name='foo',
        default=NoDefault(),
        metadata={},
    ),
)


def test_extra_at_list():
    layouts = make_layouts(
        TestField('a'),
        name_mapping(
            map={
                'a': 0,
            },
            extra_in=ExtraSkip(),
            extra_out=ExtraSkip(),
        ),
        DEFAULT_NAME_MAPPING,
    )
    assert layouts == Layouts(
        InputNameLayout(
            crown=InpListCrown(
                map=[
                    InpFieldCrown('a'),
                ],
                extra_policy=ExtraSkip(),
            ),
            extra_move=None,
        ),
        OutputNameLayout(
            crown=OutListCrown(
                map=[
                    OutFieldCrown('a'),
                ],
            ),
            extra_move=None,
        ),
    )

    layouts = make_layouts(
        TestField('a'),
        name_mapping(
            map={
                'a': 0,
            },
            extra_in=ExtraForbid(),
            extra_out=ExtraSkip(),
        ),
        DEFAULT_NAME_MAPPING,
    )
    assert layouts == Layouts(
        InputNameLayout(
            crown=InpListCrown(
                map=[
                    InpFieldCrown('a'),
                ],
                extra_policy=ExtraForbid(),
            ),
            extra_move=None,
        ),
        OutputNameLayout(
            crown=OutListCrown(
                map=[
                    OutFieldCrown('a'),
                ],
            ),
            extra_move=None,
        ),
    )

    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Can not use collecting extra_in with list mapping"
        )
    ):
        make_layouts(
            TestField('a'),
            TestField('b'),
            name_mapping(
                map={
                    'a': 0,
                },
                extra_in='b',
                extra_out='b',
            ),
            DEFAULT_NAME_MAPPING,
        )

    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Can not use collecting extra_in with list mapping"
            " at type <class 'tests.unit.provider.name_layout.test_provider.Foo'>"
        )
    ):
        make_layouts(
            TestField('a'),
            TestField('b'),
            name_mapping(
                map={
                    'a': 0,
                },
                extra_in='b',
                extra_out='b',
            ),
            DEFAULT_NAME_MAPPING,
            loc_map=TYPE_HINT_LOC_MAP,
        )

    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Can not use collecting extra_in with list mapping"
            " at type <class 'tests.unit.provider.name_layout.test_provider.Foo'> that situated at field 'foo'"
        )
    ):
        make_layouts(
            TestField('a'),
            TestField('b'),
            name_mapping(
                map={
                    'a': 0,
                },
                extra_in='b',
                extra_out='b',
            ),
            DEFAULT_NAME_MAPPING,
            loc_map=FIELD_LOC_MAP,
        )


def test_required_field_skip():
    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Required fields ['a'] are skipped"
        )
    ):
        make_layouts(
            TestField('a', is_required=True),
            TestField('b', is_required=True),
            name_mapping(
                skip=['a'],
            ),
            DEFAULT_NAME_MAPPING,
        )

    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Required fields ['a'] are skipped at type <class 'tests.unit.provider.name_layout.test_provider.Foo'>"
        ),
    ):
        make_layouts(
            TestField('a', is_required=True),
            TestField('b', is_required=True),
            name_mapping(
                skip=['a'],
            ),
            DEFAULT_NAME_MAPPING,
            loc_map=TYPE_HINT_LOC_MAP,
        )

    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Required fields ['a'] are skipped at type <class 'tests.unit.provider.name_layout.test_provider.Foo'>"
            " that situated at field 'foo'"
        ),
    ):
        make_layouts(
            TestField('a', is_required=True),
            TestField('b', is_required=True),
            name_mapping(
                skip=['a'],
            ),
            DEFAULT_NAME_MAPPING,
            loc_map=FIELD_LOC_MAP,
        )


def test_inconsistent_path_elements():
    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Inconsistent path elements at ('x',)"
        ),
    ):
        make_layouts(
            TestField('a', is_required=True),
            TestField('b', is_required=True),
            name_mapping(
                map={
                    'a': ('x', 'y'),
                    'b': ('x', 0),
                },
            ),
            DEFAULT_NAME_MAPPING,
        )

    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Inconsistent path elements at ('x',) at type <class 'tests.unit.provider.name_layout.test_provider.Foo'>"
        ),
    ):
        make_layouts(
            TestField('a', is_required=True),
            TestField('b', is_required=True),
            name_mapping(
                map={
                    'a': ('x', 'y'),
                    'b': ('x', 0),
                },
            ),
            DEFAULT_NAME_MAPPING,
            loc_map=TYPE_HINT_LOC_MAP,
        )

    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Inconsistent path elements at ('x',) at type <class 'tests.unit.provider.name_layout.test_provider.Foo'>"
            " that situated at field 'foo'"
        ),
    ):
        make_layouts(
            TestField('a', is_required=True),
            TestField('b', is_required=True),
            name_mapping(
                map={
                    'a': ('x', 'y'),
                    'b': ('x', 0),
                },
            ),
            DEFAULT_NAME_MAPPING,
            loc_map=FIELD_LOC_MAP,
        )


def test_duplicated_path():
    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Paths {('x',): ['a', 'b']} pointed to several fields"
        ),
    ):
        make_layouts(
            TestField('a'),
            TestField('b'),
            name_mapping(
                map={
                    'a': 'x',
                    'b': 'x',
                },
            ),
            DEFAULT_NAME_MAPPING,
        )

    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Paths {('x',): ['a', 'b']} pointed to several fields"
            " at type <class 'tests.unit.provider.name_layout.test_provider.Foo'>"
        ),
    ):
        make_layouts(
            TestField('a'),
            TestField('b'),
            name_mapping(
                map={
                    'a': 'x',
                    'b': 'x',
                },
            ),
            DEFAULT_NAME_MAPPING,
            loc_map=TYPE_HINT_LOC_MAP,
        )

    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Paths {('x',): ['a', 'b']} pointed to several fields"
            " at type <class 'tests.unit.provider.name_layout.test_provider.Foo'> that situated at field 'foo'"
        ),
    ):
        make_layouts(
            TestField('a'),
            TestField('b'),
            name_mapping(
                map={
                    'a': 'x',
                    'b': 'x',
                },
            ),
            DEFAULT_NAME_MAPPING,
            loc_map=FIELD_LOC_MAP,
        )


def test_optional_field_at_list():
    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Optional fields ['b'] can not be mapped to list elements"
        ),
    ):
        make_layouts(
            TestField('a', is_required=True),
            TestField('b', is_required=False),
            name_mapping(
                map={
                    'a': 0,
                    'b': 1,
                },
            ),
            DEFAULT_NAME_MAPPING,
        )

    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Optional fields ['b'] can not be mapped to list elements"
            " at type <class 'tests.unit.provider.name_layout.test_provider.Foo'>"
        ),
    ):
        make_layouts(
            TestField('a', is_required=True),
            TestField('b', is_required=False),
            name_mapping(
                map={
                    'a': 0,
                    'b': 1,
                },
            ),
            DEFAULT_NAME_MAPPING,
            loc_map=TYPE_HINT_LOC_MAP,
        )

    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Optional fields ['b'] can not be mapped to list elements"
            " at type <class 'tests.unit.provider.name_layout.test_provider.Foo'> that situated at field 'foo'"
        ),
    ):
        make_layouts(
            TestField('a', is_required=True),
            TestField('b', is_required=False),
            name_mapping(
                map={
                    'a': 0,
                    'b': 1,
                },
            ),
            DEFAULT_NAME_MAPPING,
            loc_map=FIELD_LOC_MAP,
        )


def test_one_path_is_prefix_of_another():
    with pytest.raises(
        ValueError,
        match=full_match_regex_str(
            "Path to the field must not be a prefix of another path"
            " at type <class 'tests.unit.provider.name_layout.test_provider.Foo'> that situated at field 'foo'."
            " Path [0] (field 'a') is prefix of [0, 'b'] (field 'b'), [0, 'c'] (field 'c')"
        ),
    ):
        make_layouts(
            TestField('a', is_required=True),
            TestField('b', is_required=True),
            TestField('c', is_required=True),
            name_mapping(
                map={
                    'a': 0,
                    'b': (0, 'b'),
                    'c': (0, 'c'),
                },
            ),
            DEFAULT_NAME_MAPPING,
            loc_map=FIELD_LOC_MAP,
        )



def test_chaining_priority():
    layouts = make_layouts(
        TestField('a'),
        name_mapping(
            map={
                'a': 'x',
            },
        ),
        name_mapping(
            map={
                'a': 'y',
            },
        ),
        DEFAULT_NAME_MAPPING,
    )
    assert layouts == Layouts(
        InputNameLayout(
            crown=InpDictCrown(
                map={'x': InpFieldCrown('a')},
                extra_policy=ExtraSkip(),
            ),
            extra_move=None,
        ),
        OutputNameLayout(
            crown=OutDictCrown(
                map={'x': OutFieldCrown('a')},
                sieves={},
            ),
            extra_move=None,
        ),
    )


def test_ellipsis_replacing_str_key():
    layouts = make_layouts(
        TestField('a_'),
        TestField('b'),
        name_mapping(
            name_style=NameStyle.UPPER,
            map=[
                ('.*', ('data', ...)),
            ],
        ),
        DEFAULT_NAME_MAPPING,
    )
    assert layouts == Layouts(
        InputNameLayout(
            crown=InpDictCrown(
                map={
                    'data': InpDictCrown(
                        map={
                            'A': InpFieldCrown('a_'),
                            'B': InpFieldCrown('b'),
                        },
                        extra_policy=ExtraSkip(),
                    ),
                },
                extra_policy=ExtraSkip(),
            ),
            extra_move=None,
        ),
        OutputNameLayout(
            crown=OutDictCrown(
                map={
                    'data': OutDictCrown(
                        map={
                            'A': OutFieldCrown('a_'),
                            'B': OutFieldCrown('b'),
                        },
                        sieves={},
                    ),
                },
                sieves={},
            ),
            extra_move=None,
        ),
    )


def test_ellipsis_replacing_int_key():
    layouts = make_layouts(
        TestField('a_'),
        TestField('b'),
        name_mapping(
            as_list=True,
            map=[
                ('.*', ('data', ...)),
            ],
        ),
        DEFAULT_NAME_MAPPING,
    )
    assert layouts == Layouts(
        InputNameLayout(
            crown=InpDictCrown(
                map={
                    'data': InpListCrown(
                        map=[
                            InpFieldCrown('a_'),
                            InpFieldCrown('b'),
                        ],
                        extra_policy=ExtraSkip(),
                    ),
                },
                extra_policy=ExtraSkip(),
            ),
            extra_move=None,
        ),
        OutputNameLayout(
            crown=OutDictCrown(
                map={
                    'data': OutListCrown(
                        map=[
                            OutFieldCrown('a_'),
                            OutFieldCrown('b'),
                        ],
                    ),
                },
                sieves={},
            ),
            extra_move=None,
        ),
    )


def test_empty_models_dict():
    layouts = make_layouts(
        DEFAULT_NAME_MAPPING,
    )
    assert layouts == Layouts(
        InputNameLayout(
            crown=InpDictCrown(
                map={},
                extra_policy=ExtraSkip(),
            ),
            extra_move=None,
        ),
        OutputNameLayout(
            crown=OutDictCrown(
                map={},
                sieves={},
            ),
            extra_move=None,
        ),
    )


def test_empty_models_list():
    layouts = make_layouts(
        name_mapping(as_list=True),
        DEFAULT_NAME_MAPPING,
    )
    assert layouts == Layouts(
        InputNameLayout(
            crown=InpListCrown(
                map=[],
                extra_policy=ExtraSkip(),
            ),
            extra_move=None,
        ),
        OutputNameLayout(
            crown=OutListCrown(
                map=[],
            ),
            extra_move=None,
        ),
    )
