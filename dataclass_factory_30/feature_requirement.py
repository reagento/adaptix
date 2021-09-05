import sys
from typing import Tuple


class VersionRequirement:
    __slots__ = ('ver', 'is_meet')

    @classmethod
    def make(cls, *ver: int):
        return cls(ver)

    def __init__(self, ver: Tuple[int, ...]):
        self.ver = ver
        self.is_meet = sys.version_info >= ver

    def __bool__(self):
        return self.is_meet

    def __call__(self, func):
        import pytest

        ver_str = '.'.join(map(str, self.ver))

        return pytest.mark.skipif(
            not self.is_meet,
            reason=f'Need Python >= {ver_str}'
        )(func)


has_protocol = VersionRequirement.make(3, 8)
has_literal = VersionRequirement.make(3, 8)
has_final = VersionRequirement.make(3, 8)
has_typed_dict = VersionRequirement.make(3, 8)

has_annotated = VersionRequirement.make(3, 9)
