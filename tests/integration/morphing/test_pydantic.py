from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, computed_field

from adaptix import Retort, as_is_loader


def test_basic(accum):
    class MyModel(BaseModel):
        f1: int
        f2: str

    retort = Retort(recipe=[accum])
    assert retort.load({"f1": 0, "f2": "a"}, MyModel) == MyModel(f1=0, f2="a")
    assert retort.dump(MyModel(f1=0, f2="a")) == {"f1": 0, "f2": "a"}


def test_all_field_kinds(accum):
    class MyModel(BaseModel):
        a: int

        @computed_field
        @property
        def b(self) -> str:
            return "b_value"

        _c: int

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._c = 2

    retort = Retort(recipe=[accum])
    assert retort.load({"a": 0}, MyModel) == MyModel(a=0)
    assert retort.dump(MyModel(a=0)) == {"a": 0, "b": "b_value"}


def test_generic():
    T1 = TypeVar("T1")
    T2 = TypeVar("T2")

    class SkipLimit(BaseModel, Generic[T1]):
        pages: int
        skip: int
        limit: int
        items: list[T1]

    class NextPrevious(SkipLimit[T2], BaseModel, Generic[T2]):
        has_next: bool
        has_previous: bool

    class BaseChat(BaseModel):
        expert_id: UUID
        owner_id: UUID
        request_id: UUID
        deadline: datetime
        updated_at: datetime

        status: Any
        users_id: list[UUID]

    class ChatWithUnreadMessages(BaseChat, BaseModel):
        id: str
        unread_messages: int

    retort = Retort(
        recipe=[
            as_is_loader(UUID),
        ],
    )
    data = {
        "pages": 1,
        "limit": 10,
        "skip": 0,
        "has_next": False,
        "has_previous": False,
        "items": [
            {
                "id": "68107997d373d077d16e98e3",
                "expert_id": UUID("bb45bd65-1ef1-49d7-b974-f666b4fc26a0"),
                "owner_id": UUID("ca3ef90e-f129-43df-bb83-db298e13c56d"),
                "request_id": UUID("fa286a75-5838-44bb-8e9c-8064996c903e"),
                "deadline": "2025-05-15T10:46:30.162196+00:00",
                "updated_at": "2025-04-29T07:02:47.453650+00:00",
                "status": "Active",
                "users_id": [UUID("ca3ef90e-f129-43df-bb83-db298e13c56d")],
                "unread_messages": 0,
            },
        ],
    }
    assert (
        retort.load(data, NextPrevious[ChatWithUnreadMessages])
        ==
        NextPrevious[ChatWithUnreadMessages](
            pages=1,
            skip=0,
            limit=10,
            items=[
                ChatWithUnreadMessages(
                    expert_id=UUID("bb45bd65-1ef1-49d7-b974-f666b4fc26a0"),
                    owner_id=UUID("ca3ef90e-f129-43df-bb83-db298e13c56d"),
                    request_id=UUID("fa286a75-5838-44bb-8e9c-8064996c903e"),
                    deadline=datetime(2025, 5, 15, 10, 46, 30, 162196, tzinfo=timezone.utc),
                    updated_at=datetime(2025, 4, 29, 7, 2, 47, 453650, tzinfo=timezone.utc),
                    status="Active",
                    users_id=[UUID("ca3ef90e-f129-43df-bb83-db298e13c56d")],
                    id="68107997d373d077d16e98e3",
                    unread_messages=0,
                ),
            ],
            has_next=False,
            has_previous=False,
        )
    )
