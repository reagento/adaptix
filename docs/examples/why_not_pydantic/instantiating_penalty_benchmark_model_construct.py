# ruff: noqa: T201
from datetime import datetime
from timeit import timeit

from .instantiating_penalty_benchmark import UserPydantic, stmt

print(
    "pydantic (model_construct)",
    timeit(stmt, globals={"User": UserPydantic.model_construct, "datetime": datetime}),
)
