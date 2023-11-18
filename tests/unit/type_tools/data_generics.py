from typing import Generic, TypeVar

_T = TypeVar('_T', covariant=True)  # make it covariant to use at protocol


class Gen(Generic[_T]):
    pass


class GenChildImplicit(Gen):
    pass


class GenChildExplicit(Gen[int]):
    pass


class GenChildExplicitTypeVar(Gen[_T]):
    pass


class GenGen(Gen[int], Generic[_T]):
    pass
