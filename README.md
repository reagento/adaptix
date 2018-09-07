# dataclass_factory

## Usage

```python
from dataclass_factory import parse

@dataclass
class D:
    a: int
    b: int = field(init=False, default=1)
    c: str = "def_value"


data = {
    "a": 1
}

obj = parse(data, D)

```

## Enums
python
```
class E(Enum):
    one = 1
    hello = "hello"

@dataclass
class D2:
    d: D
    e: E
    
    
data = {
    "d": {
        "a": 1,
        "c": "value",
    },
    "e": "hello"
}

obj = parse(data, D2)
```
