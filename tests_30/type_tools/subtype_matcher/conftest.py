from dataclass_factory_30.type_tools.subtype_matcher import DefaultSubtypeMatcher

matcher = DefaultSubtypeMatcher()


def assert_subtype_shift(sub_cls, cls):
    assert matcher.is_subtype(sub_cls, cls)
    assert not matcher.is_subtype(cls, sub_cls)


class Class:
    pass


class SubClass(Class):
    pass
