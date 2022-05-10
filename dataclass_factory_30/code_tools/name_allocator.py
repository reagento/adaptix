import string
from abc import ABC, abstractmethod
from dataclasses import dataclass, InitVar
from itertools import chain
from random import Random
from typing import TypeVar, Generic, Optional, Any, Dict, MutableSet, AbstractSet, Iterator, List, Iterable
from collections.abc import Set

T = TypeVar('T')


class AllocError(Exception):
    pass


class NameAllocator(ABC):
    @abstractmethod
    def alloc_outer(self, value: Any, name: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def alloc_local(self, name: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def alloc_prefix(self, name: Optional[str] = None) -> str:
        """Allocate prefix. Yoy can use any name that starts with allocated prefix"""


@dataclass
class Namespace:
    local: MutableSet[str]
    outer: Dict[str, Any]
    predefined: AbstractSet[str]

    prefixes: InitVar[List[str]]
    random: Random

    def __post_init__(self, prefixes):
        self._prefixes: List[str] = []

        for prefix in prefixes:
            self.add_prefix(prefix)

    def has_prefix_conflict(self, name: str) -> bool:
        return any(name.startswith(prefix) for prefix in self._prefixes)

    def add_prefix(self, prefix: str):
        if self.has_prefix_conflict(prefix):
            raise ValueError
        self._prefixes.append(prefix)

    def can_add(self, name: str) -> bool:
        return (
            name not in self
            and not self.has_prefix_conflict(name)
        )

    def __contains__(self, item):
        return item in self.predefined or item in self.outer or item in self.local


class ConflictSolver(ABC):
    @abstractmethod
    def solve(self, namespace: Namespace, name: str) -> str:
        pass


class PrefixSolver(ConflictSolver):
    def __init__(self, prefix: str):
        self._prefix = prefix

    def solve(self, namespace: Namespace, name: str) -> str:
        solved = self._prefix + name
        if solved in namespace:
            raise RuntimeError
        return solved


class DefaultNameAllocator(NameAllocator):
    RANDOM_NAME_POPULATION = string.ascii_lowercase
    RANDOM_NAME_LEN = 6
    RAND_PREFIX = 't_'

    def __init__(self, solver: ConflictSolver, namespace: Namespace):
        self.solver = solver
        self.namespace = namespace

    def alloc_outer(self, value: Any, name: Optional[str] = None) -> str:
        allocated = self._alloc(name)
        self.namespace.outer[allocated] = value
        return allocated

    def alloc_local(self, name: Optional[str] = None) -> str:
        allocated = self._alloc(name)
        self.namespace.local.add(allocated)
        return allocated

    def alloc_prefix(self, name: Optional[str] = None) -> str:
        allocated = self._alloc(name)
        self.namespace.add_prefix(allocated)
        return allocated

    def _alloc(self, name: Optional[str]) -> str:
        if name is not None:
            if self.namespace.can_add(name):
                return name

            return self.solver.solve(self.namespace, name)

        return self._gen_free_name()

    def _gen_free_name(self) -> str:
        for _ in range(150):
            name = self._get_random_name()

            if self.namespace.can_add(name):
                return name

        raise RuntimeError

    def _get_random_name(self) -> str:
        return self.RAND_PREFIX + "".join(
            self.namespace.random.choices(self.RANDOM_NAME_POPULATION, k=self.RANDOM_NAME_LEN)
        )


namespace = Namespace(...)

solver = PrefixSolver(namespace, "prefix1_")

generator(
    DefaultNameAllocator(solver, namespace),
)

solver = PrefixSolver(namespace, "prefix2_")

generator(
    DefaultNameAllocator(solver, namespace),
)


class MyPrefixSolver(ConflictSolver):
    def __init__(self, namespace: Namespace, prefixes: Set[str]):
        self._prefixes = prefixes
        self._used_prefixes = set()
        self._prefix = None

        for prefix in prefixes:
            namespace.add_prefix(prefix)

    def solve(self, namespace: Namespace, name: str) -> str:
        if self._prefix is None:
            raise RuntimeError("Prefix not set")

        solved = self._prefix + name
        if solved in namespace:
            raise RuntimeError
        return solved

    def set_prefix(self, prefix: str):
        if prefix in self._used_prefixes:
            raise ValueError("Can not use prefix twice")
        if prefix not in self._prefixes:
            raise ValueError("Can not use unknown prefix")
        self._prefix = prefix

namespace = Namespace(...)

solver = MyPrefixSolver(namespace, {"prefix1_", "prefix2_"})

solver.set_prefix("prefix1_")
generator(
    DefaultNameAllocator(solver, namespace),
)

solver.set_prefix("prefix2_")
generator(
    DefaultNameAllocator(solver, namespace),
)
