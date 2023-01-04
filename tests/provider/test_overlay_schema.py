import re
from dataclasses import dataclass
from typing import Callable, Iterable, List

import pytest

from dataclass_factory.facade import bound
from dataclass_factory.provider import Chain, Mediator, Provider, Request, StaticProvider, static_provision_action
from dataclass_factory.provider.overlay_schema import Overlay, OverlayProvider, Schema, provide_schema
from dataclass_factory.provider.request_cls import Location, TypeHintLocation
from dataclass_factory.utils import Omittable, Omitted
from tests_helpers import TestRetort, full_match_regex_str


@dataclass
class MySchema(Schema):
    number: int
    char_list: List[str]


@dataclass
class MyOverlay(Overlay[MySchema]):
    number: Omittable[int]
    char_list: Omittable[List[str]]

    def _merge_char_list(self, old: List[str], new: List[str]) -> List[str]:
        return new + old


@dataclass(frozen=True)
class SampleRequest(Request):
    pass


class SampleRequestProvider(StaticProvider):
    def __init__(self, provide_action: Callable[[Mediator], MySchema]):
        self.provide_action = provide_action

    @static_provision_action
    def _provide_overlay(self, mediator: Mediator, request: SampleRequest):
        return self.provide_action(mediator)


def provide_overlay_schema(recipe: Iterable[Provider], provide_action: Callable[[Mediator], MySchema]) -> MySchema:
    retort = TestRetort(
        recipe=[
            *recipe,
            SampleRequestProvider(provide_action),
        ]
    )
    return retort.provide(SampleRequest())


def test_simple():
    assert provide_overlay_schema(
        recipe=[
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=1,
                        char_list=['a', 'b'],
                    )
                ],
                chain=None,
            ),
        ],
        provide_action=lambda m: provide_schema(MyOverlay, m, Location())
    ) == MySchema(
        number=1,
        char_list=['a', 'b'],
    )


def test_chaining():
    assert provide_overlay_schema(
        recipe=[
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=1,
                        char_list=['a', 'b'],
                    )
                ],
                chain=Chain.FIRST,
            ),
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=2,
                        char_list=['c', 'd'],
                    )
                ],
                chain=None,
            ),
        ],
        provide_action=lambda m: provide_schema(MyOverlay, m, Location())
    ) == MySchema(
        number=1,
        char_list=['a', 'b', 'c', 'd'],
    )

    assert provide_overlay_schema(
        recipe=[
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=1,
                        char_list=['a', 'b'],
                    )
                ],
                chain=Chain.LAST,
            ),
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=2,
                        char_list=['c', 'd'],
                    )
                ],
                chain=None,
            ),
        ],
        provide_action=lambda m: provide_schema(MyOverlay, m, Location())
    ) == MySchema(
        number=2,
        char_list=['c', 'd', 'a', 'b'],
    )

    assert provide_overlay_schema(
        recipe=[
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=Omitted(),
                        char_list=['a', 'b'],
                    )
                ],
                chain=Chain.FIRST,
            ),
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=2,
                        char_list=['c', 'd'],
                    )
                ],
                chain=None,
            ),
        ],
        provide_action=lambda m: provide_schema(MyOverlay, m, Location())
    ) == MySchema(
        number=2,
        char_list=['a', 'b', 'c', 'd'],
    )

    assert provide_overlay_schema(
        recipe=[
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=1,
                        char_list=Omitted(),
                    )
                ],
                chain=Chain.FIRST,
            ),
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=2,
                        char_list=['c', 'd'],
                    )
                ],
                chain=None,
            ),
        ],
        provide_action=lambda m: provide_schema(MyOverlay, m, Location())
    ) == MySchema(
        number=1,
        char_list=['c', 'd'],
    )

    assert provide_overlay_schema(
        recipe=[
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=Omitted(),
                        char_list=Omitted(),
                    )
                ],
                chain=Chain.FIRST,
            ),
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=2,
                        char_list=['c', 'd'],
                    )
                ],
                chain=None,
            ),
        ],
        provide_action=lambda m: provide_schema(MyOverlay, m, Location())
    ) == MySchema(
        number=2,
        char_list=['c', 'd'],
    )


class MyClass1:
    pass


class MyClass2(MyClass1):
    pass


def test_typehint_location():
    assert provide_overlay_schema(
        recipe=[
            bound(
                MyClass2,
                OverlayProvider(
                    overlays=[
                        MyOverlay(
                            number=1,
                            char_list=['a', 'b'],
                        )
                    ],
                    chain=None,
                ),
            ),
            bound(
                MyClass1,
                OverlayProvider(
                    overlays=[
                        MyOverlay(
                            number=2,
                            char_list=['c', 'd'],
                        )
                    ],
                    chain=None,
                ),
            ),
        ],
        provide_action=lambda m: provide_schema(MyOverlay, m, TypeHintLocation(type=MyClass2))
    ) == MySchema(
        number=1,
        char_list=['a', 'b', 'c', 'd'],
    )

    assert provide_overlay_schema(
        recipe=[
            bound(
                MyClass2,
                OverlayProvider(
                    overlays=[
                        MyOverlay(
                            number=1,
                            char_list=['a', 'b'],
                        )
                    ],
                    chain=None,
                ),
            ),
            bound(
                MyClass1,
                OverlayProvider(
                    overlays=[
                        MyOverlay(
                            number=2,
                            char_list=['c', 'd'],
                        )
                    ],
                    chain=Chain.FIRST,
                ),
            ),
            bound(
                MyClass1,
                OverlayProvider(
                    overlays=[
                        MyOverlay(
                            number=3,
                            char_list=['e', 'f'],
                        )
                    ],
                    chain=None,
                ),
            ),
        ],
        provide_action=lambda m: provide_schema(MyOverlay, m, TypeHintLocation(type=MyClass2))
    ) == MySchema(
        number=1,
        char_list=['a', 'b', 'c', 'd', 'e', 'f'],
    )


def test_omitted_fields():
    with pytest.raises(
        ValueError,
        match=full_match_regex_str("Can not create schema because overlay contains omitted values at ['number']")
    ):
        provide_overlay_schema(
            recipe=[
                OverlayProvider(
                    overlays=[
                        MyOverlay(
                            number=Omitted(),
                            char_list=['a', 'b'],
                        )
                    ],
                    chain=Chain.FIRST,
                ),
                OverlayProvider(
                    overlays=[
                        MyOverlay(
                            number=Omitted(),
                            char_list=['c', 'd'],
                        )
                    ],
                    chain=None,
                ),
            ],
            provide_action=lambda m: provide_schema(MyOverlay, m, Location())
        )

