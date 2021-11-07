from dataclass_factory_30.type_tools import DefaultSubtypeMatcher


def assert_swapped_is_subtype(sub_tp, tp):
    assert is_subtype(sub_tp, tp)
    assert not is_subtype(tp, sub_tp)


def is_subtype(sub_tp, tp):
    return DefaultSubtypeMatcher(tp).is_subtype(sub_tp)


def match(sub_tp, tp):
    return DefaultSubtypeMatcher(tp)(sub_tp)


class Class:
    pass


class SubClass(Class):
    pass
