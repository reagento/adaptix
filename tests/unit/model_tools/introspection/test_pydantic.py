from pydantic import BaseModel


def test_basic():
    class MyModel(BaseModel):
        pass
