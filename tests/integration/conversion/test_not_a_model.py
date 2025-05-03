from dataclasses import dataclass

from tests_helpers.misc import raises_exc_text, requires

from adaptix._internal.feature_requirement import HAS_PY_310
from adaptix.conversion import get_converter


def test_source_is_not_a_model():
    class Book:
        title: str
        price: int
        author: int

    @dataclass
    class BookDTO:
        title: str
        price: int
        author: int

    raises_exc_text(
        lambda: get_converter(Book, BookDTO),
        """
        adaptix.ProviderNotFoundError: Cannot produce converter for <Signature (src: __main__.Book, /) -> __main__.BookDTO>
          × Cannot create top-level coercer
          ╰──▷ Cannot find coercer
               Linking: ‹src: Book› ──▷ BookDTO
               Hint: Type ‹Book› is not recognized as model. Did your forget `@dataclass` decorator? Check documentation what model kinds are supported
        """,
        {
            "Book": Book.__qualname__,
            "BookDTO": BookDTO.__qualname__,
            "__main__": __name__,
        },
    )


def test_destination_is_not_a_model():
    @dataclass
    class Book:
        title: str
        price: int
        author: int

    class BookDTO:
        title: str
        price: int
        author: int

    raises_exc_text(
        lambda: get_converter(Book, BookDTO),
        """
        adaptix.ProviderNotFoundError: Cannot produce converter for <Signature (src: __main__.Book, /) -> __main__.BookDTO>
          × Cannot create top-level coercer
          ╰──▷ Cannot find coercer
               Linking: ‹src: Book› ──▷ BookDTO
               Hint: Type ‹BookDTO› is not recognized as model. Did your forget `@dataclass` decorator? Check documentation what model kinds are supported
        """,
        {
            "Book": Book.__qualname__,
            "BookDTO": BookDTO.__qualname__,
            "__main__": __name__,
        },
    )


@requires(HAS_PY_310)
def test_both_are_not_a_model():
    class Book:
        title: str
        price: int
        author: int

    class BookDTO:
        title: str
        price: int
        author: int

    raises_exc_text(
        lambda: get_converter(Book, BookDTO),
        """
        adaptix.ProviderNotFoundError: Cannot produce converter for <Signature (src: __main__.Book, /) -> __main__.BookDTO>
          × Cannot create top-level coercer
          ╰──▷ Cannot find coercer
               Linking: ‹src: Book› ──▷ BookDTO
               Hint: Types are not recognized as models. Did your forget `@dataclass` decorator? Check documentation what model kinds are supported
        """,
        {
            "Book": Book.__qualname__,
            "BookDTO": BookDTO.__qualname__,
            "__main__": __name__,
        },
    )
