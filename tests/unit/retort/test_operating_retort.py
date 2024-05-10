from dataclasses import dataclass
from typing import List

import pytest
from tests_helpers import cond_list, raises_exc, with_cause, with_notes

from adaptix import AggregateCannotProvide, CannotProvide, NoSuitableProvider, Retort
from adaptix._internal.feature_requirement import HAS_STD_CLASSES_GENERICS
from adaptix.conversion import get_converter


def test_cannot_produce_loader():
    retort = Retort()

    @dataclass
    class Stub:
        f1: int
        f2: memoryview
        f3: memoryview

    raises_exc(
        with_cause(
            with_notes(
                NoSuitableProvider(f"Cannot produce loader for type {Stub}"),
                "Note: The attached exception above contains verbose description of the problem",
            ),
            with_notes(
                AggregateCannotProvide(
                    "Cannot create loader for model. Loaders for some fields cannot be created",
                    [
                        with_notes(
                            CannotProvide(
                                "Cannot find loader",
                                is_terminal=False,
                                is_demonstrative=True,
                            ),
                            f"Location: `{Stub.__qualname__}.f2: memoryview`",
                        ),
                        with_notes(
                            CannotProvide(
                                "Cannot find loader",
                                is_terminal=False,
                                is_demonstrative=True,
                            ),
                            f"Location: `{Stub.__qualname__}.f3: memoryview`",
                        ),
                    ],
                    is_terminal=True,
                    is_demonstrative=True,
                ),
                f"Location: `{Stub.__qualname__}`",
            ),
        ),
        lambda: retort.get_loader(Stub),
    )


def test_cannot_produce_dumper():
    retort = Retort()

    @dataclass
    class Stub:
        f1: int
        f2: memoryview
        f3: memoryview

    raises_exc(
        with_cause(
            with_notes(
                NoSuitableProvider(f"Cannot produce dumper for type {Stub}"),
                "Note: The attached exception above contains verbose description of the problem",
            ),
            with_notes(
                AggregateCannotProvide(
                    "Cannot create dumper for model. Dumpers for some fields cannot be created",
                    [
                        with_notes(
                            CannotProvide(
                                "Cannot find dumper",
                                is_terminal=False,
                                is_demonstrative=True,
                            ),
                            f"Location: `{Stub.__qualname__}.f2: memoryview`",
                        ),
                        with_notes(
                            CannotProvide(
                                "Cannot find dumper",
                                is_terminal=False,
                                is_demonstrative=True,
                            ),
                            f"Location: `{Stub.__qualname__}.f3: memoryview`",
                        ),
                    ],
                    is_terminal=True,
                    is_demonstrative=True,
                ),
                f"Location: `{Stub.__qualname__}`",
            ),
        ),
        lambda: retort.get_dumper(Stub),
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

    raises_exc(
        with_cause(
            with_notes(
                NoSuitableProvider(
                    f"Cannot produce converter for"
                    f" <Signature (src: {Book.__module__}.{Book.__qualname__}, /)"
                    f" -> {BookDTO.__module__}.{BookDTO.__qualname__}>",
                ),
                "Note: The attached exception above contains verbose description of the problem",
            ),
            AggregateCannotProvide(
                "Cannot create top-level coercer",
                [
                    with_notes(
                        AggregateCannotProvide(
                            "Cannot create coercer for models. Linkings for some fields are not found",
                            [
                                with_notes(
                                    CannotProvide(
                                        f"Cannot find paired field of `{BookDTO.__qualname__}.author: str` for linking",
                                        is_terminal=False,
                                        is_demonstrative=True,
                                    ),
                                    "Note: This is a required field, so it must take value",
                                ),
                            ],
                            is_terminal=True,
                            is_demonstrative=True,
                        ),
                        f"Linking: `{Book.__qualname__} => {BookDTO.__qualname__}`",
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
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

    raises_exc(
        with_cause(
            with_notes(
                NoSuitableProvider(
                    f"Cannot produce converter for"
                    f" <Signature (src: {Book.__module__}.{Book.__qualname__}, /)"
                    f" -> {BookDTO.__module__}.{BookDTO.__qualname__}>",
                ),
                "Note: The attached exception above contains verbose description of the problem",
            ),
            AggregateCannotProvide(
                "Cannot create top-level coercer",
                [
                    with_notes(
                        AggregateCannotProvide(
                            "Cannot create coercer for models. Linkings for some fields are not found",
                            [
                                with_notes(
                                    CannotProvide(
                                        f"Cannot find paired field of `{BookDTO.__qualname__}.author: str` for linking",
                                        is_terminal=False,
                                        is_demonstrative=True,
                                    ),
                                    "Note: Current policy forbids unlinked optional fields,"
                                    " so you need to link it to another field"
                                    " or explicitly confirm the desire to skipping using `allow_unlinked_optional`",
                                ),
                            ],
                            is_terminal=True,
                            is_demonstrative=True,
                        ),
                        f"Linking: `{Book.__qualname__} => {BookDTO.__qualname__}`",
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
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

    raises_exc(
        with_cause(
            with_notes(
                NoSuitableProvider(
                    f"Cannot produce converter for"
                    f" <Signature (src: {Book.__module__}.{Book.__qualname__}, /)"
                    f" -> {BookDTO.__module__}.{BookDTO.__qualname__}>",
                ),
                "Note: The attached exception above contains verbose description of the problem",
            ),
            AggregateCannotProvide(
                "Cannot create top-level coercer",
                [
                    with_notes(
                        AggregateCannotProvide(
                            "Cannot create coercer for models. Coercers for some linkings are not found",
                            [
                                with_notes(
                                    CannotProvide(
                                        "Cannot find coercer",
                                        is_terminal=False,
                                        is_demonstrative=True,
                                    ),
                                    f"Linking: `{Book.__qualname__}.author: int => {BookDTO.__qualname__}.author: str`",
                                ),
                            ],
                            is_terminal=True,
                            is_demonstrative=True,
                        ),
                        f"Linking: `{Book.__qualname__} => {BookDTO.__qualname__}`",
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
    )


@pytest.mark.parametrize(
    ["list_tp", "list_tp_name"],
    [
        pytest.param(List, "List"),
        *cond_list(HAS_STD_CLASSES_GENERICS, [pytest.param(list, "list")]),
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

    raises_exc(
        with_cause(
            with_notes(
                NoSuitableProvider(
                    f"Cannot produce converter for"
                    f" <Signature (src: {Book.__module__}.{Book.__qualname__}, /)"
                    f" -> {BookDTO.__module__}.{BookDTO.__qualname__}>",
                ),
                "Note: The attached exception above contains verbose description of the problem",
            ),
            AggregateCannotProvide(
                "Cannot create top-level coercer",
                [
                    with_notes(
                        AggregateCannotProvide(
                            "Cannot create coercer for models. Coercers for some linkings are not found",
                            [
                                with_notes(
                                    AggregateCannotProvide(
                                        "Cannot create coercer for iterables. Coercer for element cannot be created",
                                        [
                                            with_notes(
                                                CannotProvide(
                                                    "Cannot find coercer",
                                                    is_terminal=False,
                                                    is_demonstrative=True,
                                                ),
                                                "Linking: `str => int`",
                                            ),
                                        ],
                                        is_terminal=True,
                                        is_demonstrative=True,
                                    ),
                                    f"Linking:"
                                    f" `{Book.__qualname__}.authors: {list_tp_name}[str]"
                                    f" => {BookDTO.__qualname__}.authors: {list_tp_name}[int]`",
                                ),
                            ],
                            is_terminal=True,
                            is_demonstrative=True,
                        ),
                        f"Linking: `{Book.__qualname__} => {BookDTO.__qualname__}`",
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
    )
