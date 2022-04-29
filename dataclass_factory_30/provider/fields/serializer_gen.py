from typing import Dict, Set

from dataclass_factory_30.code_tools import ClosureCompiler, CodeBuilder
from dataclass_factory_30.common import Serializer
from dataclass_factory_30.provider import OutputFieldsFigure
from dataclass_factory_30.provider.code_gen_basics import CodeGenHook, RootCrown, FldPathElem
from dataclass_factory_30.provider.fields_basics import InpDictCrown, Crown, ListCrown


class GenState:

    def get_field_serializer_var_name(self, field_name: str) -> str:
        return f"serializer_{field_name}"


class FieldsSerializerGenerator:
    def __init__(
        self,
        figure: OutputFieldsFigure,
        omit_default: Set[str],
    ):
        self.figure = figure
        self.omit_default = omit_default
        self.field_name_to_field: Dict[str, InputFieldRM] = {
            field.name: field for field in self.figure.fields
        }

    def generate(
        self,
        compiler: ClosureCompiler,
        field_serializers: Dict[str, Serializer],
        root_crown: RootCrown,
        closure_name: str,
        file_name: str,
        hook: CodeGenHook,
    ) -> Serializer:
        pass

    def _gen_crown_dispatch(self, builder: CodeBuilder, state: GenState, sub_crown: Crown, key: FldPathElem):
        with state.add_key(key):
            if self._gen_root_crown_dispatch(builder, state, sub_crown):
                return builder
            if isinstance(sub_crown, FieldCrown):
                self._gen_field_crown(builder, state, sub_crown)
                return builder
            if sub_crown is None:
                return builder

            raise ValueError

    def _gen_dict_crown(self, builder: CodeBuilder, state: GenState, crown: InpDictCrown):

        with builder("{"):
            for k, v in crown.map.items():
                if k in self.omit_default:
                    continue

                sub = self._gen_crown_dispatch(builder.sub(), state, v, k).string()
                builder(
                    f"{k!r}: {sub},"
                )

        builder("}")

    def _gen_list_crown(self, builder: CodeBuilder, state: GenState, crown: ListCrown):
        builder("[")

        with builder:
            for k, v in crown.map.items():
                self._gen_crown_dispatch(builder, state, v, k)

        builder("]")


