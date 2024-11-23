# ruff: noqa: T201
from datetime import datetime
from timeit import timeit

from .instantiating_penalty_models import UserDataclass, UserPydantic

stmt = """
User(
    id=123,
    signup_ts=dt,
    tastes={'wine': 9, 'cheese': 7, 'cabbage': '1'},
)
"""
dt = datetime(year=2019, month=6, day=1, hour=12, minute=22)
print(
    "pydantic                  ",
    timeit(stmt, globals={"User": UserPydantic, "dt": dt}),
)
print(
    "pydantic (model_construct)",
    timeit(stmt, globals={"User": UserPydantic.model_construct, "dt": dt}),
)
print(
    "dataclass                 ",
    timeit(stmt, globals={"User": UserDataclass, "dt": dt}),
)
