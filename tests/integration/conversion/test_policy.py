from tests_helpers import ModelSpec, exclude_model_spec

from adaptix.conversion import allow_unlinked_optional, impl_converter


@exclude_model_spec(ModelSpec.TYPED_DICT)
def test_unbound_optional(src_model_spec, dst_model_spec):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: str
        field2: str

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: str
        field2: str
        wild: str = ""

    @impl_converter(recipe=[allow_unlinked_optional("wild")])
    def convert(a: SourceModel) -> DestModel:
        ...

    if dst_model_spec.kind == ModelSpec.SQLALCHEMY:
        # sqlalchemy set default after flush
        assert convert(SourceModel(field1="1", field2="2")) == DestModel(field1="1", field2="2")
    else:
        assert convert(SourceModel(field1="1", field2="2")) == DestModel(field1="1", field2="2", wild="")
