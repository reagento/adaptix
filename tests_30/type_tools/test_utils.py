import sys
from typing import NamedTuple
from collections import namedtuple

import pytest

from dataclass_factory_30.type_tools import is_named_tuple_class, is_protocol


class NTParent(NamedTuple):
    a: int
    b: int


class NTChild(NTParent):
    c: int


DynNTParent = namedtuple('DynNTParent', 'a, b')


class DynNTChild(DynNTParent):
    c: int


def test_is_named_tuple_class():
    assert is_named_tuple_class(NTParent)
    assert is_named_tuple_class(NTChild)
    assert is_named_tuple_class(DynNTParent)
    assert is_named_tuple_class(DynNTChild)


@pytest.mark.skipif(sys.version_info < (3, 8), reason='Need Python >= 3.8')
def test_is_protocol():
    from typing import Protocol, runtime_checkable
    from typing import SupportsInt

    class Proto(Protocol):
        def foo(self) -> bool:
            pass

    @runtime_checkable
    class RtProto(Protocol):
        def foo(self) -> bool:
            pass

    class ImplProto:
        def foo(self) -> bool:
            pass

    class InheritedImplProto(Proto):
        def foo(self) -> bool:
            pass

    class InheritedImplRtProto(RtProto):
        def foo(self) -> bool:
            pass

    assert not is_protocol(Protocol)
    assert is_protocol(Proto)
    assert is_protocol(RtProto)
    assert is_protocol(SupportsInt)

    assert not is_protocol(InheritedImplProto)
    assert not is_protocol(InheritedImplRtProto)

    assert not is_protocol(ImplProto)
    assert not is_protocol(int)
    assert not is_protocol(type)
    assert not is_protocol(object)

    assert not is_protocol(15)
    assert not is_protocol('15')

    class ExtProto(Proto, Protocol):
        def bar(self):
            pass

    assert is_protocol(ExtProto)
