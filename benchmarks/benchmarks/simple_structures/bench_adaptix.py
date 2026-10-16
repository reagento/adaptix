from dataclasses import dataclass
from typing import List

import pytest

from adaptix import CodeGenBackend, DebugTrail, Retort, name_mapping
from benchmarks.native_backend import benchmark_env_spec, skip_native
from benchmarks.pybench.bench_api import benchmark_plan
from benchmarks.simple_structures.common import create_book, create_dumped_book


@dataclass
class Review:
    id: int
    title: str
    rating: float
    content: str


@dataclass
class Book:
    id: int
    name: str
    reviews: List[Review]


retort = Retort(
    recipe=[
        name_mapping(Review, map={"content": "text"}),
    ],
)


@pytest.mark.parametrize("codegen_backend", list(CodeGenBackend))
def test_loading(codegen_backend):
    if codegen_backend == CodeGenBackend.X86_64 and skip_native(benchmark_env_spec()):
        pytest.skip("Native code generation is unsupported on this platform")
    assert (
        retort.replace(codegen_backend=codegen_backend).load(create_dumped_book(reviews_count=1), Book)
        ==
        create_book(Book, Review, reviews_count=1)
    )


@pytest.mark.parametrize("codegen_backend", list(CodeGenBackend))
def test_dumping(codegen_backend):
    if codegen_backend == CodeGenBackend.X86_64 and skip_native(benchmark_env_spec()):
        pytest.skip("Native code generation is unsupported on this platform")
    assert (
        retort.replace(codegen_backend=codegen_backend).dump(create_book(Book, Review, reviews_count=1))
        ==
        create_dumped_book(reviews_count=1)
    )


def bench_loading(strict_coercion: bool, debug_trail: str, reviews_count: int, codegen_backend: str):
    loader = retort.replace(
        strict_coercion=strict_coercion,
        debug_trail=DebugTrail(debug_trail),
        codegen_backend=CodeGenBackend(codegen_backend),
    ).get_loader(Book)

    data = create_dumped_book(reviews_count=reviews_count)
    return benchmark_plan(loader, data)


def bench_dumping(debug_trail: str, reviews_count: int, codegen_backend: str):
    dumper = retort.replace(
        debug_trail=DebugTrail(debug_trail),
        codegen_backend=CodeGenBackend(codegen_backend),
    ).get_dumper(Book)

    data = create_book(Book, Review, reviews_count=reviews_count)
    return benchmark_plan(dumper, data)
