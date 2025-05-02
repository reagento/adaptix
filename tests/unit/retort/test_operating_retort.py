from dataclasses import dataclass
from typing import List

import pytest
from tests_helpers.misc import raises_exc_text

from adaptix import Retort
from adaptix.conversion import get_converter


def test_cannot_produce_loader():
    retort = Retort()

    @dataclass
    class Stub:
        f1: int
        f2: memoryview
        f3: memoryview

    raises_exc_text(
        lambda: retort.get_loader(Stub),
        """
        adaptix.ProviderNotFoundError: Cannot produce loader for type <class '__main__.Stub'>
          × Cannot create loader for model. Loaders for some fields cannot be created
          │ Location: ‹Stub›
          ├──▷ Cannot find loader
          │    Location: ‹Stub.f2: memoryview›
          ╰──▷ Cannot find loader
               Location: ‹Stub.f3: memoryview›
        """,
        {
            "Stub": Stub.__qualname__,
            "__main__": __name__,
        },
    )


def test_cannot_produce_dumper():
    retort = Retort()

    @dataclass
    class Stub:
        f1: int
        f2: memoryview
        f3: memoryview

    raises_exc_text(
        lambda: retort.get_dumper(Stub),
        """
        adaptix.ProviderNotFoundError: Cannot produce dumper for type <class '__main__.Stub'>
          × Cannot create dumper for model. Dumpers for some fields cannot be created
          │ Location: ‹Stub›
          ├──▷ Cannot find dumper
          │    Location: ‹Stub.f2: memoryview›
          ╰──▷ Cannot find dumper
               Location: ‹Stub.f3: memoryview›
        """,
        {
            "Stub": Stub.__qualname__,
            "__main__": __name__,
        },
    )


def test_cannot_produce_converter_no_linking_required():
    @dataclass
    class Book:
        title: str
        price: int

    @dataclass
    class BookDTO:
        title: str
        price: int
        author: str

    raises_exc_text(
        lambda: get_converter(Book, BookDTO),
        """
        adaptix.ProviderNotFoundError: Cannot produce converter for <Signature (src: __main__.Book, /) -> __main__.BookDTO>
          × Cannot create top-level coercer
          ╰──▷ Cannot create coercer for models. Linkings for some fields are not found
             │ Linking: ‹src: Book› ──▷ BookDTO
             ╰──▷ Cannot find paired field of ‹BookDTO.author: str› for linking
                  Note: This is a required field, so it must take value
        """,
        {
            "Book": Book.__qualname__,
            "BookDTO": BookDTO.__qualname__,
            "__main__": __name__,
        },
    )


def test_cannot_produce_converter_no_linking_optional():
    @dataclass
    class Book:
        title: str
        price: int

    @dataclass
    class BookDTO:
        title: str
        price: int
        author: str = ""

    raises_exc_text(
        lambda: get_converter(Book, BookDTO),
        """
        adaptix.ProviderNotFoundError: Cannot produce converter for <Signature (src: __main__.Book, /) -> __main__.BookDTO>
          × Cannot create top-level coercer
          ╰──▷ Cannot create coercer for models. Linkings for some fields are not found
             │ Linking: ‹src: Book› ──▷ BookDTO
             ╰──▷ Cannot find paired field of ‹BookDTO.author: str› for linking
                  Note: Current policy forbids unlinked optional fields, so you need to link it to another field or explicitly confirm the desire to skipping using `allow_unlinked_optional`
        """,
        {
            "Book": Book.__qualname__,
            "BookDTO": BookDTO.__qualname__,
            "__main__": __name__,
        },
    )


def test_cannot_produce_converter_no_coercer():
    @dataclass
    class Book:
        title: str
        price: int
        author: int

    @dataclass
    class BookDTO:
        title: str
        price: int
        author: str

    raises_exc_text(
        lambda: get_converter(Book, BookDTO),
        """
        adaptix.ProviderNotFoundError: Cannot produce converter for <Signature (src: __main__.Book, /) -> __main__.BookDTO>
          × Cannot create top-level coercer
          ╰──▷ Cannot create coercer for models. Coercers for some linkings are not found
             │ Linking: ‹src: Book› ──▷ BookDTO
             ╰──▷ Cannot find coercer
                  Linking: ‹Book.author: int› ──▷ ‹BookDTO.author: str›
        """,
        {
            "Book": Book.__qualname__,
            "BookDTO": BookDTO.__qualname__,
            "__main__": __name__,
        },
    )


@pytest.mark.parametrize(
    ["list_tp", "list_tp_name"],
    [
        pytest.param(List, "List"),
        pytest.param(list, "list"),
    ],
)
def test_cannot_produce_converter_no_coercer_complex_type(list_tp, list_tp_name):
    @dataclass
    class Book:
        title: str
        price: int
        authors: list_tp[str]

    @dataclass
    class BookDTO:
        title: str
        price: int
        authors: list_tp[int]

    raises_exc_text(
        lambda: get_converter(Book, BookDTO),
        """
        adaptix.ProviderNotFoundError: Cannot produce converter for <Signature (src: __main__.Book, /) -> __main__.BookDTO>
          × Cannot create top-level coercer
          ╰──▷ Cannot create coercer for models. Coercers for some linkings are not found
             │ Linking: ‹src: Book› ──▷ BookDTO
             ╰──▷ Cannot create coercer for iterables. Coercer for element cannot be created
                │ Linking: ‹Book.authors: list[str]› ──▷ ‹BookDTO.authors: list[int]›
                ╰──▷ Cannot find coercer
                     Linking: str ──▷ int
        """,
        {
            "Book": Book.__qualname__,
            "BookDTO": BookDTO.__qualname__,
            "list": list_tp_name,
            "__main__": __name__,
        },
    )
