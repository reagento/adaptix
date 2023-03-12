from dataclasses import dataclass
from types import FunctionType
from typing import Any, Dict, Optional, Union

import pytest

from adaptix import bound, name_mapping
from adaptix._internal.model_tools import (
    AttrAccessor,
    Default,
    DefaultFactory,
    DefaultValue,
    InputField,
    InputFigure,
    NoDefault,
    OutputField,
    OutputFigure,
    ParamKind,
    ParamKwargs,
)
from adaptix._internal.provider import (
    BuiltinInputExtractionMaker,
    BuiltinOutputCreationMaker,
    InputFigureRequest,
    InputNameLayoutRequest,
    ModelDumperProvider,
    ModelLoaderProvider,
    NameSanitizer,
    NameStyle,
    OutputFigureRequest,
    OutputNameLayoutRequest,
    Provider,
    ValueProvider,
    make_input_creation,
    make_output_extraction,
)
from adaptix._internal.provider.model import (
    ExtraForbid,
    ExtraSkip,
    InpDictCrown,
    InpFieldCrown,
    InputNameLayout,
    OutDictCrown,
    OutFieldCrown,
    OutputNameLayout,
)
from adaptix._internal.provider.model.crown_definitions import (
    ExtraCollect,
    ExtraExtract,
    ExtraKwargs,
    ExtraSaturate,
    ExtraTargets,
    InpListCrown,
    InpNoneCrown,
    OutListCrown,
    OutNoneCrown,
)
from adaptix._internal.provider.name_layout import (
    BuiltinExtraMoveAndPoliciesMaker,
    BuiltinNameLayoutProvider,
    BuiltinSievesMaker,
    BuiltinStructureMaker,
)
from adaptix._internal.provider.request_cls import (
    DebugPathRequest,
    DumperRequest,
    FieldLoc,
    LoaderRequest,
    LocMap,
    StrictCoercionRequest,
    TypeHintLoc,
)
from tests_helpers import TestRetort, full_match_regex_str, type_of


@dataclass
class TestField:
    name: str
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
    input_figure = InputFigure(
        fields=tuple(
            InputField(
                name=fld.name,
                type=Any,
                default=fld.default,
                metadata={},
                is_required=fld.is_required,
                param_kind=ParamKind.POS_OR_KW,
                param_name=fld.name,
            )
            for fld in fields
        ),
        constructor=stub,
        kwargs=ParamKwargs(Any),
        overriden_types=frozenset(fld.name for fld in fields),
    )
    output_figure = OutputFigure(
        fields=tuple(
            OutputField(
                name=fld.name,
                type=Any,
                default=fld.default,
                metadata={},
                accessor=AttrAccessor(
                    attr_name=fld.name,
                    is_required=fld.is_required,
                ),
            )
            for fld in fields
        ),
        overriden_types=frozenset(fld.name for fld in fields),
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
            ValueProvider(InputFigureRequest, input_figure),
            ValueProvider(OutputFigureRequest, output_figure),
            ModelLoaderProvider(NameSanitizer(), BuiltinInputExtractionMaker(), make_input_creation),
            ModelDumperProvider(NameSanitizer(), make_output_extraction, BuiltinOutputCreationMaker()),
        ]
    ).replace(
        strict_coercion=True,
        debug_path=True,
    )
    inp_request = InputNameLayoutRequest(
        loc_map=loc_map,
        figure=input_figure,
    )
    out_request = OutputNameLayoutRequest(
        loc_map=loc_map,
        figure=output_figure,
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
    only_mapped=False,
    only=None,
    map={},
    trim_trailing_underscore=True,
    name_style=None,
    omit_default=True,
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
                sieves={
                    'c': type_of(FunctionType),
                },
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
        crown.name: key  # type: ignore
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
            only_mapped=False,
            only=None,
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
            only_mapped=True,
            only=None,
            map={},
        ),
        {
            'a': None,
            'b': None,
            'c': None,
        },
    )
    assert_flat_name_mapping(
        name_mapping(
            skip=[],
            only_mapped=True,
            only=None,
            map={'a': 'z'},
        ),
        {
            'a': 'z',
            'b': None,
            'c': None,
        },
    )
    assert_flat_name_mapping(
        name_mapping(
            skip=[],
            only_mapped=False,
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
            skip=[],
            only_mapped=True,
            only=['a'],
            map={'b': 'y'}
        ),
        {
            'a': 'a',
            'b': 'y',
            'c': None,
        },
    )
    assert_flat_name_mapping(
        name_mapping(
            skip=['b'],
            only_mapped=False,
            only=None,
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
            only_mapped=False,
            only=['a', 'b'],
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
            only_mapped=True,
            only=None,
            map={'a': 'z', 'b': 'y'}
        ),
        {
            'a': 'z',
            'b': None,
            'c': None,
        },
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
                    InpFieldCrown(name='a'),
                    InpNoneCrown(),
                    InpFieldCrown(name='b'),
                ],
                extra_policy=ExtraSkip()
            ),
            extra_move=None,
        ),
        out=OutputNameLayout(
            crown=OutListCrown(
                map=[
                    OutFieldCrown(name='a'),
                    OutNoneCrown(filler=DefaultValue(value=None)),
                    OutFieldCrown(name='b')
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
                    'f': InpFieldCrown(name='f'),
                    'w': InpListCrown(
                        map=[
                            InpFieldCrown(name='d'),
                        ],
                        extra_policy=ExtraSkip(),
                    ),
                    'x': InpDictCrown(
                        map={
                            'e': InpFieldCrown(name='e'),
                            'y': InpListCrown(
                                map=[
                                    InpFieldCrown(name='a'),
                                    InpFieldCrown(name='b'),
                                ],
                                extra_policy=ExtraSkip(),
                            ),
                            'z': InpFieldCrown(name='c'),
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
                    'f': OutFieldCrown(name='f'),
                    'w': OutListCrown(
                        map=[
                            OutFieldCrown(name='d'),
                        ]
                    ),
                    'x': OutDictCrown(
                        map={
                            'e': OutFieldCrown(name='e'),
                            'y': OutListCrown(
                                map=[
                                    OutFieldCrown(name='a'),
                                    OutFieldCrown(name='b'),
                                ]
                            ),
                            'z': OutFieldCrown(name='c')
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
            " at type <class 'tests.provider.name_layout.test_provider.Foo'>"
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
            " at type <class 'tests.provider.name_layout.test_provider.Foo'> that situated at field 'foo'"
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
            "Required fields ['a'] are skipped at type <class 'tests.provider.name_layout.test_provider.Foo'>"
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
            "Required fields ['a'] are skipped at type <class 'tests.provider.name_layout.test_provider.Foo'>"
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
            "Inconsistent path elements at ('x',) at type <class 'tests.provider.name_layout.test_provider.Foo'>"
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
            "Inconsistent path elements at ('x',) at type <class 'tests.provider.name_layout.test_provider.Foo'>"
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
            " at type <class 'tests.provider.name_layout.test_provider.Foo'>"
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
            " at type <class 'tests.provider.name_layout.test_provider.Foo'> that situated at field 'foo'"
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
            " at type <class 'tests.provider.name_layout.test_provider.Foo'>"
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
            " at type <class 'tests.provider.name_layout.test_provider.Foo'> that situated at field 'foo'"
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
