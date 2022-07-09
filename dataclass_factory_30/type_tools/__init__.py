from .basic_utils import (
    is_subclass_soft, is_new_type, is_annotated,
    is_typed_dict_class, is_named_tuple_class, strip_alias,
    is_protocol, create_union, is_user_defined_generic,
)
from .norm_utils import strip_tags, is_generic
from .normalize_type import normalize_type, NormType, NormTV, BaseNormType
