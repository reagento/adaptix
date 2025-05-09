from dataclasses import dataclass
from typing import Callable, Iterable

import pytest
from tests_helpers import full_match

from adaptix import AdornedRetort, Chain, Mediator, Omittable, Omitted, Provider, Request, bound
from adaptix._internal.common import VarTuple
from adaptix._internal.provider.loc_stack_filtering import LocStack
from adaptix._internal.provider.location import TypeHintLoc
from adaptix._internal.provider.methods_provider import MethodsProvider, method_handler
from adaptix._internal.provider.overlay_schema import Overlay, OverlayProvider, Schema, provide_schema


@dataclass(frozen=True)
class MySchema(Schema):
    number: int
    char_list: VarTuple[str]


@dataclass(frozen=True)
class MyOverlay(Overlay[MySchema]):
    number: Omittable[int]
    char_list: Omittable[VarTuple[str]]

    def _merge_char_list(self, old: VarTuple[str], new: VarTuple[str]) -> VarTuple[str]:
        return new + old


@dataclass(frozen=True)
class SampleRequest(Request):
    pass


class SampleRequestProvider(MethodsProvider):
    def __init__(self, provide_action: Callable[[Mediator], MySchema]):
        self.provide_action = provide_action

    @method_handler
    def _provide_overlay(self, mediator: Mediator, request: SampleRequest):
        return self.provide_action(mediator)


def provide_overlay_schema(recipe: Iterable[Provider], provide_action: Callable[[Mediator], MySchema]) -> MySchema:
    retort = AdornedRetort(
        recipe=[
            *recipe,
            SampleRequestProvider(provide_action),
        ],
    )

    request = SampleRequest()
    return retort._facade_provide(request, error_message=f"cannot provide {request}")


class MyClass1:
    pass


class MyClass2(MyClass1):
    pass


def provide_myclass1(mediator):
    return provide_schema(MyOverlay, mediator, LocStack(TypeHintLoc(object)))


def test_simple():
    assert provide_overlay_schema(
        recipe=[
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=1,
                        char_list=("a", "b"),
                    ),
                ],
                chain=None,
            ),
        ],
        provide_action=provide_myclass1,
    ) == MySchema(
        number=1,
        char_list=("a", "b"),
    )


def test_chaining():
    assert provide_overlay_schema(
        recipe=[
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=1,
                        char_list=("a", "b"),
                    ),
                ],
                chain=Chain.FIRST,
            ),
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=2,
                        char_list=("c", "d"),
                    ),
                ],
                chain=None,
            ),
        ],
        provide_action=provide_myclass1,
    ) == MySchema(
        number=1,
        char_list=("a", "b", "c", "d"),
    )

    assert provide_overlay_schema(
        recipe=[
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=1,
                        char_list=("a", "b"),
                    ),
                ],
                chain=Chain.LAST,
            ),
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=2,
                        char_list=("c", "d"),
                    ),
                ],
                chain=None,
            ),
        ],
        provide_action=provide_myclass1,
    ) == MySchema(
        number=2,
        char_list=("c", "d", "a", "b"),
    )

    assert provide_overlay_schema(
        recipe=[
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=Omitted(),
                        char_list=("a", "b"),
                    ),
                ],
                chain=Chain.FIRST,
            ),
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=2,
                        char_list=("c", "d"),
                    ),
                ],
                chain=None,
            ),
        ],
        provide_action=provide_myclass1,
    ) == MySchema(
        number=2,
        char_list=("a", "b", "c", "d"),
    )

    assert provide_overlay_schema(
        recipe=[
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=1,
                        char_list=Omitted(),
                    ),
                ],
                chain=Chain.FIRST,
            ),
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=2,
                        char_list=("c", "d"),
                    ),
                ],
                chain=None,
            ),
        ],
        provide_action=provide_myclass1,
    ) == MySchema(
        number=1,
        char_list=("c", "d"),
    )

    assert provide_overlay_schema(
        recipe=[
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=Omitted(),
                        char_list=Omitted(),
                    ),
                ],
                chain=Chain.FIRST,
            ),
            OverlayProvider(
                overlays=[
                    MyOverlay(
                        number=2,
                        char_list=("c", "d"),
                    ),
                ],
                chain=None,
            ),
        ],
        provide_action=provide_myclass1,
    ) == MySchema(
        number=2,
        char_list=("c", "d"),
    )


def test_typehint_location():
    assert provide_overlay_schema(
        recipe=[
            bound(
                MyClass2,
                OverlayProvider(
                    overlays=[
                        MyOverlay(
                            number=1,
                            char_list=("a", "b"),
                        ),
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
                            char_list=("c", "d"),
                        ),
                    ],
                    chain=None,
                ),
            ),
        ],
        provide_action=lambda m: provide_schema(MyOverlay, m, LocStack(TypeHintLoc(type=MyClass2))),
    ) == MySchema(
        number=1,
        char_list=("a", "b", "c", "d"),
    )

    assert provide_overlay_schema(
        recipe=[
            bound(
                MyClass2,
                OverlayProvider(
                    overlays=[
                        MyOverlay(
                            number=1,
                            char_list=("a", "b"),
                        ),
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
                            char_list=("c", "d"),
                        ),
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
                            char_list=("e", "f"),
                        ),
                    ],
                    chain=None,
                ),
            ),
        ],
        provide_action=lambda m: provide_schema(MyOverlay, m, LocStack(TypeHintLoc(type=MyClass2))),
    ) == MySchema(
        number=1,
        char_list=("a", "b", "c", "d", "e", "f"),
    )


def test_omitted_fields():
    with pytest.raises(
        ValueError,
        match=full_match("Cannot create schema because overlay contains omitted values at ['number']"),
    ):
        provide_overlay_schema(
            recipe=[
                OverlayProvider(
                    overlays=[
                        MyOverlay(
                            number=Omitted(),
                            char_list=("a", "b"),
                        ),
                    ],
                    chain=Chain.FIRST,
                ),
                OverlayProvider(
                    overlays=[
                        MyOverlay(
                            number=Omitted(),
                            char_list=("c", "d"),
                        ),
                    ],
                    chain=None,
                ),
            ],
            provide_action=provide_myclass1,
        )
