# ruff: noqa: T201
from datetime import datetime
from timeit import timeit

from .instantiating_penalty_models import UserDataclass, UserPydantic

stmt = """
User(
    id=123,
    signup_ts=datetime(year=2019, month=6, day=1, hour=12, minute=22),
    tastes={'wine': 9, 'cheese': 7, 'cabbage': '1'},
)
"""
print("pydantic ", timeit(stmt, globals={"User": UserPydantic, "datetime": datetime}))
print("dataclass", timeit(stmt, globals={"User": UserDataclass, "datetime": datetime}))
