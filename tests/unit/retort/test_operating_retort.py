from dataclasses import dataclass

from tests_helpers import raises_exc, with_cause, with_notes

from adaptix import AggregateCannotProvide, CannotProvide, NoSuitableProvider, Retort
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
            NoSuitableProvider(f'Cannot produce loader for type {Stub}'),
            with_notes(
                AggregateCannotProvide(
                    'Cannot create loader for model. Loaders for some fields cannot be created',
                    [
                        with_notes(
                            CannotProvide(
                                'There is no provider that can create specified loader',
                                is_terminal=False,
                                is_demonstrative=True,
                            ),
                            f"Exception was raised while processing field 'f2' of {Stub}",
                            "Location: type=<class 'memoryview'>, field_id='f2',"
                            " default=NoDefault(), metadata=mappingproxy({}), is_required=True",
                        ),
                        with_notes(
                            CannotProvide(
                                'There is no provider that can create specified loader',
                                is_terminal=False,
                                is_demonstrative=True,
                            ),
                            f"Exception was raised while processing field 'f3' of {Stub}",
                            "Location: type=<class 'memoryview'>, field_id='f3',"
                            " default=NoDefault(), metadata=mappingproxy({}), is_required=True",
                        ),
                    ],
                    is_terminal=True,
                    is_demonstrative=True,
                ),
                f"Location: type={Stub}",
            )
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
            NoSuitableProvider(f'Cannot produce dumper for type {Stub}'),
            with_notes(
                AggregateCannotProvide(
                    'Cannot create dumper for model. Dumpers for some fields cannot be created',
                    [
                        with_notes(
                            CannotProvide(
                                'There is no provider that can create specified dumper',
                                is_terminal=False,
                                is_demonstrative=True,
                            ),
                            f"Exception was raised while processing field 'f2' of {Stub}",
                            "Location: type=<class 'memoryview'>, field_id='f2',"
                            " default=NoDefault(), metadata=mappingproxy({}),"
                            " accessor=DescriptorAccessor(attr_name='f2', access_error=None)",
                        ),
                        with_notes(
                            CannotProvide(
                                'There is no provider that can create specified dumper',
                                is_terminal=False,
                                is_demonstrative=True,
                            ),
                            f"Exception was raised while processing field 'f3' of {Stub}",
                            "Location: type=<class 'memoryview'>, field_id='f3',"
                            " default=NoDefault(), metadata=mappingproxy({}),"
                            " accessor=DescriptorAccessor(attr_name='f3', access_error=None)",
                        ),
                    ],
                    is_terminal=True,
                    is_demonstrative=True,
                ),
                f"Location: type={Stub}",
            )
        ),
        lambda: retort.get_dumper(Stub),
    )


def test_cannot_produce_converter_no_binding_required():
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
            NoSuitableProvider(
                f'Cannot produce converter for'
                f' <Signature (src: {Book.__module__}.{Book.__qualname__}, /)'
                f' -> {BookDTO.__module__}.{BookDTO.__qualname__}>'
            ),
            AggregateCannotProvide(
                'Bindings for some fields are not found',
                [
                    with_notes(
                        CannotProvide(
                            f'Cannot find paired field of `{BookDTO.__qualname__}.author` for binding',
                            is_terminal=False,
                            is_demonstrative=True,
                        ),
                        'Note: This is a required filed, so it must take value',
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
    )


def test_cannot_produce_converter_no_binding_optional():
    @dataclass
    class Book:
        title: str
        price: int

    @dataclass
    class BookDTO:
        title: str
        price: int
        author: str = ''

    raises_exc(
        with_cause(
            NoSuitableProvider(
                f'Cannot produce converter for'
                f' <Signature (src: {Book.__module__}.{Book.__qualname__}, /)'
                f' -> {BookDTO.__module__}.{BookDTO.__qualname__}>'
            ),
            AggregateCannotProvide(
                'Bindings for some fields are not found',
                [
                    with_notes(
                        CannotProvide(
                            f'Cannot find paired field of `{BookDTO.__qualname__}.author` for binding',
                            is_terminal=False,
                            is_demonstrative=True,
                        ),
                        'Note: Current policy limits unbound optional fields,'
                        ' so you need to link it to another field'
                        ' or explicitly confirm the desire to skipping using `allow_unbound_optional`',
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
            NoSuitableProvider(
                f'Cannot produce converter for'
                f' <Signature (src: {Book.__module__}.{Book.__qualname__}, /)'
                f' -> {BookDTO.__module__}.{BookDTO.__qualname__}>'
            ),
            AggregateCannotProvide(
                'Coercers for some bindings are not found',
                [
                    CannotProvide(
                        f'Cannot find coercer for binding'
                        f' `{Book.__qualname__}.author -> {BookDTO.__qualname__}.author`',
                        is_terminal=False,
                        is_demonstrative=True,
                    ),
                ],
                is_terminal=True,
                is_demonstrative=True,
            ),
        ),
        lambda: get_converter(Book, BookDTO),
    )
