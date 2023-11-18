class Gen[_T]:
    pass


class GenChildImplicit(Gen):
    pass


class GenChildExplicit(Gen[int]):
    pass


class GenChildExplicitTypeVar[_T](Gen[_T]):
    pass


class GenGen[_T](Gen[int]):
    pass
