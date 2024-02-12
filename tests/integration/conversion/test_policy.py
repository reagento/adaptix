from tests_helpers import ModelSpec, exclude_model_spec

from adaptix.conversion import allow_unlinked_optional, get_converter, impl_converter

from .local_helpers import FactoryWay


@exclude_model_spec(ModelSpec.TYPED_DICT)
def test_unbound_optional(src_model_spec, dst_model_spec, factory_way):
    @src_model_spec.decorator
    class SourceModel(*src_model_spec.bases):
        field1: str
        field2: str

    @dst_model_spec.decorator
    class DestModel(*dst_model_spec.bases):
        field1: str
        field2: str
        wild: str = ''

    if factory_way == FactoryWay.IMPL_CONVERTER:
        @impl_converter(recipe=[allow_unlinked_optional('wild')])
        def convert(a: SourceModel) -> DestModel:
            ...
    else:
        convert = get_converter(SourceModel, DestModel, recipe=[allow_unlinked_optional('wild')])

    assert convert(SourceModel(field1='1', field2='2')) == DestModel(field1='1', field2='2', wild='')
