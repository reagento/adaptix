from typing import Generic, TypeVar

_T_co = TypeVar("_T_co", covariant=True)  # make it covariant to use at protocol


class Gen(Generic[_T_co]):
    pass


class GenChildImplicit(Gen):
    pass


class GenChildExplicit(Gen[int]):
    pass


class GenChildExplicitTypeVar(Gen[_T_co]):
    pass


class GenGen(Gen[int], Generic[_T_co]):
    pass
