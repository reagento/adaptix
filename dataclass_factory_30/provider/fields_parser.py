import contextlib
import itertools
import string
from collections import deque
from dataclasses import dataclass, replace
from typing import Dict, Tuple, Set, Any, Callable, List, Union, Iterable, TypeVar, Collection

from .definitions import (
    NoRequiredFieldsError,
    NoRequiredItemsError, TypeParseError,
    ExtraItemsError, ExtraFieldsError, ParseError
)
from .essential import Mediator, CannotProvide, Request
from .fields_basics import (
    ExtraForbid, ExtraCollect,
    InputFieldsFigure,
    NameMapping, Crown,
    DictCrown, ListCrown, FieldCrown,
    InputFFRequest, InputNameMappingRequest,
    ExtraKwargs, ExtraTargets,
)
from .provider_template import ParserProvider
from .request_cls import ParserRequest, ParserFieldRequest, InputFieldRM, ParamKind
from .static_provider import StaticProvider, static_provision_action
from ..code_tools import CodeBuilder, ClosureCompiler, BasicClosureCompiler
from ..common import Parser

FldPathElem = Union[str, int]
Path = Tuple[FldPathElem, ...]
RootCrown = Union[DictCrown, ListCrown]


class GenState:
    def __init__(self, name_to_field: Dict[str, InputFieldRM]):
        self._name_to_field = name_to_field
        self.field_name2path: Dict[str, Path] = {}
        self.path2suffix: Dict[Path, str] = {}
        self.path2known_fields: Dict[Path, Set[str]] = {}

        self._path_idx = 0
        self._path: Path = ()

    def _get_path_suffix(self, path: Path) -> str:
        try:
            return self.path2suffix[path]
        except KeyError:
            self._path_idx += 1
            suffix = str(self._path_idx)
            self.path2suffix[path] = suffix
            return suffix

    def _get_var_name(self, base: str, path: Path):
        if not path:
            return base
        return base + "_" + self._get_path_suffix(path)

    def get_data_var_name(self, path=None):
        if path is None:
            path = self._path
        return self._get_var_name("data", path)

    def get_extra_var_name(self):
        return self._get_var_name("extra", self._path)

    def get_known_fields_var_name(self, path=None):
        if path is None:
            path = self._path
        return self._get_var_name("known_fields", path)

    def get_field_parser_var_name(self, field_name: str) -> str:
        return f"parser_{field_name}"

    def get_field_var_name(self, field: InputFieldRM) -> str:
        return f"f_{field.field_name}"

    def get_opt_fields_var_name(self) -> str:
        return "opt_fields"

    def get_field_var(self, field_name: str) -> str:
        return f"f_{field_name}"

    def get_raw_field_var(self, field_name: str) -> str:
        return f"r_{field_name}"

    def get_field(self, crown: FieldCrown) -> InputFieldRM:
        if crown.name in self.field_name2path:
            raise ValueError(f"{crown} appears twice")

        self.field_name2path[crown.name] = self._path
        return self._name_to_field[crown.name]

    @property
    def path(self):
        return self._path

    @contextlib.contextmanager
    def add_key(self, key: FldPathElem):
        past = self._path
        self._path += (key,)
        yield
        self._path = past


@dataclass
class CodeGenHookData:
    namespace: Dict[str, Any]
    source: str


CodeGenHook = Callable[[CodeGenHookData], None]


class FieldsParserGenerator:
    """FieldsParserGenerator creates source code of fields parser.

    For example, if fields figure is

        InputFieldsFigure(
            constructor=SampleClass,
            fields=(
                InputFieldRM(
                    field_name='z',
                    is_required=True,
                    param_kind=ParamKind.POS_OR_KW,
                    ...
                ),
                InputFieldRM(
                    field_name='y',
                    is_required=False,
                    param_kind=ParamKind.POS_OR_KW,
                    ...
                ),
            ),
            extra=ExtraKwargs(),
        )

    and root crown is

        DictCrown(
            map={
                'a': FieldCrown('z'),
                'b': FieldCrown('y'),
            },
            extra=ExtraCollect(),
        )

    output of code generator will be

        constructor = g_constructor
        known_fields = {'a', 'b'}
        parser_z = g_parser_z
        parser_y = g_parser_y

        def fields_parser_SampleClass(data):
            # field to path
            # z -> ['a']
            # y -> ['b']

            opt_fields = {}
            if not isinstance(data, dict):
                raise TypeParseError(dict, )

            extra = {}
            for key in set(data) - known_fields:
                extra[key] = data[key]

            try:
                r_z = data['a']
            except KeyError:
                raise NoRequiredFieldsError(['a'], )

            try:
                f_z = parser_z(r_z)
            except ParseError as e:
                e.append_path('a')
                raise e

            try:
                r_y = data['b']
            except KeyError:
                pass
            else:
                try:
                    opt_fields['y'] = parser_y(r_y)
                except ParseError as e:
                    e.append_path('b')
                    raise e

            return constructor(
                f_z,
                **opt_fields,
                **extra
            )
        return fields_parser_SampleClass

    for

        InputFieldsFigure(
            constructor=SampleClass,
            fields=(
                InputFieldRM(
                    field_name='z',
                    is_required=True,
                    param_kind=ParamKind.POS_ONLY,
                    ...
                ),
                InputFieldRM(
                    field_name='y',
                    is_required=True,
                    param_kind=ParamKind.KW_ONLY,
                    ...
                ),
                InputFieldRM(
                    field_name='x',
                    is_required=True,
                    param_kind=ParamKind.KW_ONLY,
                    ...
                ),
                InputFieldRM(
                    field_name='w',
                    is_required=False,
                    param_kind=ParamKind.KW_ONLY,
                    ...
                ),
            ),
            extra=ExtraTargets(('x', 'w')),
        )

    and

        NameMapping(
            crown=DictCrown(
                map={
                    'a': FieldCrown('z'),
                    'b': FieldCrown('y'),
                },
                extra=ExtraCollect(),
            ),
            skipped_extra_targets=['w'],
        )

    output will be

        constructor = g_constructor
        known_fields = {'b', 'a'}
        parser_z = g_parser_z
        parser_y = g_parser_y
        parser_x = g_parser_x

        def fields_parser_SampleClass(data):
            # field to path
            # z -> ['a']
            # y -> ['b']

            if not isinstance(data, dict):
                raise TypeParseError(dict, )

            extra = {}
            for key in set(data) - known_fields:
                extra[key] = data[key]

            try:
                r_z = data['a']
            except KeyError:
                raise NoRequiredFieldsError(['a'], )

            try:
                f_z = parser_z(r_z)
            except ParseError as e:
                e.append_path('a')
                raise e

            try:
                r_y = data['b']
            except KeyError:
                raise NoRequiredFieldsError(['b'], )

            try:
                f_y = parser_y(r_y)
            except ParseError as e:
                e.append_path('b')
                raise e

            f_x = parser_x(extra)

            return constructor(
                f_z,
                y=f_y,
                x=f_x,
            )
        return fields_parser_SampleClass

    """

    def __init__(
        self,
        figure: InputFieldsFigure,
        debug_path: bool,
        strict_coercion: bool,
    ):
        self.debug_path = debug_path
        self.strict_coercion = strict_coercion
        self.figure = figure
        self.field_name_to_field: Dict[str, InputFieldRM] = {
            field.field_name: field for field in self.figure.fields
        }

    def _gen_header(self, builder: CodeBuilder, state: GenState):
        if state.path2suffix:
            builder += "# suffix to path"
            for path, suffix in state.path2suffix.items():
                builder += f"# {suffix} -> {list(path)}"

            builder.empty_line()

        if state.field_name2path:
            builder += "# field to path"
            for f_name, path in state.field_name2path.items():
                builder += f"# {f_name} -> {list(path)}"

            builder.empty_line()

    def _create_state(self):
        return GenState(self.field_name_to_field)

    def generate(
        self,
        compiler: ClosureCompiler,
        field_parsers: Dict[str, Parser],
        root_crown: RootCrown,
        closure_name: str,
        file_name: str,
        hook: CodeGenHook,
    ) -> Parser:
        """Create parser.
        Method generates body of function that produces closure
        and pass it to ClosureCompiler.
        """
        state = self._create_state()

        parser_body_builder = self._gen_parser_body(root_crown, state)

        builder = CodeBuilder()

        # copy global variables to local namespace capturing it's by closure
        self._gen_local_assignment(
            builder,
            {'constructor': 'g_constructor'},
            {
                state.get_known_fields_var_name(path): repr(known_fields)
                for path, known_fields in state.path2known_fields.items()
            },
            {
                var: f'g_{var}'
                for var in (
                    state.get_field_parser_var_name(field_name)
                    for field_name in field_parsers
                )
            },
        )

        builder.empty_line()

        data = state.get_data_var_name()
        with builder(f"def {closure_name}({data}):"):
            builder.extend(parser_body_builder)

        builder += f"return {closure_name}"

        namespace = {
            "g_constructor": self.figure.constructor,
            "deque": deque,
            **{
                "g_" + state.get_field_parser_var_name(field_name): parser
                for field_name, parser in field_parsers.items()
            },
            **{
                e.__name__: e
                for e in [
                    ExtraFieldsError, ExtraItemsError,
                    TypeParseError, NoRequiredFieldsError,
                    ParseError
                ]
            },
        }

        hook(
            CodeGenHookData(
                namespace=namespace, source=builder.string()
            )
        )

        return compiler.compile(
            builder,
            file_name,
            namespace,
        )

    def _gen_local_assignment(self, builder: CodeBuilder, *local_to_literals: Dict[str, str]):
        for local_to_lit in local_to_literals:
            for l_var, literal in local_to_lit.items():
                builder(f"{l_var} = {literal}")

    def _gen_extra_targets_assigment(self, builder: CodeBuilder, state: GenState, root_crown: RootCrown):
        # Saturate extra targets with data.
        # If extra data is not collected, parser of required field will get empty dict
        if not isinstance(self.figure.extra, ExtraTargets):
            return

        if root_crown.extra == ExtraCollect():
            for target in self.figure.extra.fields:
                self._gen_field_assigment(
                    builder,
                    field_left_value=state.get_field_var(target),
                    field_name=target,
                    data_for_parser=state.get_extra_var_name(),
                    state=state,
                )
        else:
            for target in self.figure.extra.fields:
                if self.field_name_to_field[target].is_required:
                    self._gen_field_assigment(
                        builder,
                        field_left_value=state.get_field_var(target),
                        field_name=target,
                        data_for_parser="{}",
                        state=state,
                    )

        builder.empty_line()

    def _field_is_extra_target(self, field: InputFieldRM):
        return (
            isinstance(self.figure.extra, ExtraTargets)
            and
            field.field_name in self.figure.extra.fields
        )

    def _gen_parser_body(self, root_crown: RootCrown, state: GenState) -> CodeBuilder:
        """Creates parser body which consist of 4 elements:
        1. Header of comments containing debug data
        2. Mapping external structure to fields (this mapping defined by Crown)
        3. Passing extra data to extra targets
        4. Passing fields to constructor parameters
        """
        has_opt_params = any(
            not f.is_required and not self._field_is_extra_target(f)
            for f in self.figure.fields
        )
        opt_fields = state.get_opt_fields_var_name()

        s_builder = CodeBuilder()

        if has_opt_params:
            s_builder(f"{opt_fields} = {{}}")

        if not self._gen_root_crown_dispatch(s_builder, state, root_crown):
            raise ValueError

        builder = CodeBuilder()
        self._gen_header(builder, state)

        builder.extend(s_builder)

        self._gen_extra_targets_assigment(
            builder, state, root_crown
        )

        builder += """
            return constructor(
        """

        with builder:
            for field in self.figure.fields:
                self._gen_field_passing(builder, state, field)

            if has_opt_params:
                builder += f"**{opt_fields},"

            if (
                root_crown.extra == ExtraCollect()
                and
                self.figure.extra == ExtraKwargs()
            ):
                extra = state.get_extra_var_name()
                builder += f"**{extra}"

        builder += ")"

        return builder

    def _gen_field_passing(self, builder: CodeBuilder, state: GenState, field: InputFieldRM):
        if field.is_required:
            param = field.field_name
            var = state.get_field_var(field.field_name)

            if field.param_kind == ParamKind.KW_ONLY:
                builder(f"{param}={var},")
            else:
                builder(f"{var},")

    def _gen_root_crown_dispatch(self, builder: CodeBuilder, state: GenState, crown: Crown):
        """Returns True if code is generated"""
        if isinstance(crown, DictCrown):
            self._gen_dict_crown(builder, state, crown)
        elif isinstance(crown, ListCrown):
            self._gen_list_crown(builder, state, crown)
        else:
            return False
        return True

    def _gen_crown_dispatch(self, builder: CodeBuilder, state: GenState, sub_crown: Crown, key: FldPathElem):
        with state.add_key(key):
            if self._gen_root_crown_dispatch(builder, state, sub_crown):
                return
            if isinstance(sub_crown, FieldCrown):
                self._gen_field_crown(builder, state, sub_crown)
                return
            if sub_crown is None:
                return

            raise ValueError

    def _get_path_lit(self, path: Path) -> str:
        return repr(deque(path)) if self.debug_path and len(path) > 0 else ""

    def _gen_var_assigment_from_data(
        self,
        builder: CodeBuilder,
        state: GenState,
        var: str,
        ignore_lookup_error=False
    ):
        last_path_el = state.path[-1]
        before_path = state.path[:-1]

        if isinstance(last_path_el, str):
            error = KeyError.__name__
            parse_error = NoRequiredFieldsError.__name__
        else:
            error = IndexError.__name__
            parse_error = NoRequiredItemsError.__name__

        path_lit = self._get_path_lit(before_path)
        data = state.get_data_var_name(state.path[:-1])
        last_path_el = repr(last_path_el)

        if ignore_lookup_error:
            on_error = "pass"
        else:
            on_error = f"raise {parse_error}([{last_path_el}], {path_lit})"

        builder(
            f"""
            try:
                {var} = {data}[{last_path_el}]
            except {error}:
                {on_error}
            """,
        )

    def _gen_dict_crown(self, builder: CodeBuilder, state: GenState, crown: DictCrown):
        if crown.extra in (ExtraForbid(), ExtraCollect()):
            known_fields = set(crown.map.keys())
            state.path2known_fields[state.path] = known_fields

        known_fields = state.get_known_fields_var_name()
        data = state.get_data_var_name()
        extra = state.get_extra_var_name()
        path_lit = self._get_path_lit(state.path)

        if state.path:
            self._gen_var_assigment_from_data(
                builder, state, state.get_data_var_name(),
            )
            builder.empty_line()

        builder += f"""
            if not isinstance({data}, dict):
                raise TypeParseError(dict, {path_lit})
        """

        builder.empty_line()

        if crown.extra == ExtraForbid():
            builder += f"""
                {extra} = set({data}) - {known_fields}
                if {extra}:
                    raise ExtraFieldsError({extra}, {path_lit})
            """
            builder.empty_line()

        elif crown.extra == ExtraCollect():
            builder += f"""
                {extra} = {{}}
                for key in set({data}) - {known_fields}:
                    {extra}[key] = {data}[key]
            """
            builder.empty_line()

        for key, value in crown.map.items():
            self._gen_crown_dispatch(builder, state, value, key)

    def _gen_list_crown(self, builder: CodeBuilder, state: GenState, crown: ListCrown):
        data = state.get_data_var_name()
        path_lit = self._get_path_lit(state.path)
        list_len = str(crown.list_len)

        if state.path:
            self._gen_var_assigment_from_data(
                builder, state, state.get_data_var_name(),
            )
            builder.empty_line()

        builder += f"""
            if not isinstance({data}, list):
                raise TypeParseError(list, {path_lit})
        """

        builder.empty_line()

        if crown.extra == ExtraForbid():
            builder += f"""
                if len({data}) > {list_len}:
                    raise ExtraItemsError({list_len}, {path_lit})
            """
            builder.empty_line()

        for key, value in crown.map.items():
            self._gen_crown_dispatch(builder, state, value, key)

    def _gen_field_crown(self, builder: CodeBuilder, state: GenState, crown: FieldCrown):
        field = state.get_field(crown)

        if field.is_required:
            field_left_value = state.get_field_var(field.field_name)
        else:
            opt_fields = state.get_opt_fields_var_name()
            field_left_value = f"{opt_fields}[{field.field_name!r}]"

        self._gen_var_assigment_from_data(
            builder,
            state,
            state.get_raw_field_var(crown.name),
            ignore_lookup_error=not field.is_required,
        )
        data_for_parser = state.get_raw_field_var(field.field_name)

        if field.is_required:
            builder.empty_line()
            self._gen_field_assigment(
                builder,
                field_left_value,
                field.field_name,
                data_for_parser,
                state,
            )
        else:
            with builder("else:"):
                self._gen_field_assigment(
                    builder,
                    field_left_value,
                    field.field_name,
                    data_for_parser,
                    state,
                )

        builder.empty_line()

    def _gen_field_assigment(
        self,
        builder: CodeBuilder,
        field_left_value: str,
        field_name: str,
        data_for_parser: str,
        state: GenState,
    ):
        field_parser = state.get_field_parser_var_name(field_name)

        if self.debug_path and state.path:
            last_path_el = repr(state.path[-1])

            builder(
                f"""
                try:
                    {field_left_value} = {field_parser}({data_for_parser})
                except ParseError as e:
                    e.append_path({last_path_el})
                    raise e
                """
            )
        else:
            builder(
                f"{field_left_value} = {field_parser}({data_for_parser})"
            )


@dataclass(frozen=True)
class CodeGenHookRequest(Request[CodeGenHook]):
    initial_request: Request


def _stub_code_gen_hook(data: CodeGenHookData):
    pass


class CodeGenAccumulator(StaticProvider):
    """Accumulates all generated code. It may be useful for debugging"""

    def __init__(self):
        self.list: List[Tuple[Request, CodeGenHookData]] = []

    @static_provision_action(CodeGenHookRequest)
    def _provide_code_gen_hook(self, mediator: Mediator, request: CodeGenHookRequest) -> CodeGenHook:
        def hook(data: CodeGenHookData):
            self.list.append((request.initial_request, data))

        return hook


_AVAILABLE_CHARS = set(string.ascii_letters + string.digits)

T = TypeVar('T')


def _merge_iters(args: Iterable[Iterable[T]]) -> List[T]:
    return list(itertools.chain.from_iterable(args))


class FieldsParserProvider(ParserProvider):
    def _sanitize_name(self, name: str):
        if name == "":
            return ""

        first_letter = name[0]

        if first_letter not in string.ascii_letters:
            return self._sanitize_name(name[1:])

        return first_letter + "".join(
            c for c in name[1:] if c in _AVAILABLE_CHARS
        )

    def _get_closure_name(self, request: ParserRequest) -> str:
        tp = request.type
        if isinstance(tp, type):
            name = tp.__name__
        else:
            name = str(tp)

        s_name = self._sanitize_name(name)
        if s_name != "":
            s_name = "_" + s_name
        return "fields_parser" + s_name

    def _get_file_name(self, request: ParserRequest) -> str:
        return self._get_closure_name(request)

    def _collect_used_fields(self, crown: Crown) -> List[str]:
        if isinstance(crown, (DictCrown, ListCrown)):
            return _merge_iters(
                self._collect_used_fields(sub_crown)
                for sub_crown in crown.map.values()
            )
        if isinstance(crown, FieldCrown):
            return [crown.name]
        if crown is None:
            return []
        raise RuntimeError

    def _field_is_skipped(
        self,
        field: InputFieldRM,
        skipped_extra_targets: Collection[str],
        used_fields: Set[str],
        extra_targets: Set[str]
    ):
        f_name = field.field_name
        if f_name in extra_targets:
            return f_name in skipped_extra_targets
        else:
            return f_name not in used_fields

    def _process_figure(self, figure: InputFieldsFigure, name_mapping: NameMapping) -> InputFieldsFigure:
        used_fields = set(self._collect_used_fields(name_mapping.crown))

        if isinstance(figure.extra, ExtraTargets):
            extra_targets = set(figure.extra.fields)

            extra_targets_at_crown = used_fields & extra_targets
            if extra_targets_at_crown:
                raise ValueError(
                    f"Fields {extra_targets_at_crown} can not be extra target"
                    f" and be presented at name_mapping"
                )
        else:
            extra_targets = set()

        skipped_required_fields = [
            field.field_name
            for field in figure.fields
            if field.is_required and self._field_is_skipped(
                field,
                skipped_extra_targets=name_mapping.skipped_extra_targets,
                used_fields=used_fields,
                extra_targets=extra_targets
            )
        ]
        if skipped_required_fields:
            raise ValueError(
                f"Required fields {skipped_required_fields} not presented at name_mapping crown"
            )

        filtered_extra_targets = extra_targets - set(name_mapping.skipped_extra_targets)

        extra = figure.extra

        if isinstance(extra, ExtraTargets):
            extra = ExtraTargets(tuple(filtered_extra_targets))

        # leave only fields that will be passed to constructor
        new_figure = replace(
            figure,
            fields=tuple(
                fld for fld in figure.fields
                if fld.field_name in used_fields or fld.field_name in filtered_extra_targets
            ),
            extra=extra,
        )

        return new_figure

    def _get_compiler(self):
        return BasicClosureCompiler()

    def _make_parser(
        self,
        figure: InputFieldsFigure,
        request: ParserRequest,
        field_parsers: Dict[str, Parser],
        root_crown: RootCrown,
        code_gen_hook: CodeGenHook,
    ):
        generator = FieldsParserGenerator(
            figure=figure,
            debug_path=request.debug_path,
            strict_coercion=request.strict_coercion,
        )

        return generator.generate(
            compiler=self._get_compiler(),
            field_parsers=field_parsers,
            root_crown=root_crown,
            hook=code_gen_hook,
            closure_name=self._get_closure_name(request),
            file_name=self._get_file_name(request),
        )

    def _provide_parser(self, mediator: Mediator, request: ParserRequest) -> Parser:
        figure: InputFieldsFigure = mediator.provide(
            InputFFRequest(type=request.type)
        )
        name_mapping: NameMapping = mediator.provide(
            InputNameMappingRequest(type=request.type, figure=figure)
        )

        if name_mapping.crown.extra == ExtraCollect() and figure.extra is None:
            raise CannotProvide(
                "Cannot create parser that collect extra data"
                " if InputFieldsFigure does not take extra data"
            )

        try:
            code_gen_hook = mediator.provide(CodeGenHookRequest(initial_request=request))
        except CannotProvide:
            code_gen_hook = _stub_code_gen_hook

        new_figure = self._process_figure(figure, name_mapping)

        field_parsers = {
            field.field_name: mediator.provide(
                ParserFieldRequest(
                    type=field.type,
                    strict_coercion=request.strict_coercion,
                    debug_path=request.debug_path,
                    default=field.default,
                    is_required=field.is_required,
                    metadata=field.metadata,
                    field_name=field.field_name,
                    param_kind=field.param_kind,
                )
            )
            for field in new_figure.fields
        }

        return self._make_parser(
            figure=new_figure,
            request=request,
            field_parsers=field_parsers,
            root_crown=name_mapping.crown,
            code_gen_hook=code_gen_hook,
        )
