import itertools
from typing import Any, Dict, Iterable, Iterator, Mapping, Optional, TypeVar

P = TypeVar("P", bound="Parametrizer")


class Parametrizer:
    def __init__(self, *, product: Optional[Mapping[str, Iterable[Any]]] = None) -> None:
        self._product: Dict[str, Iterable[Any]] = {} if product is None else dict(product)

    def product(self: P, variants: Mapping[str, Iterable[Any]]) -> P:
        self._product.update(variants)
        return self

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        for case_values in itertools.product(*self._product.values()):
            yield dict(zip(self._product.keys(), case_values))


def bool_tag_spec(key: str, tag: Optional[str] = None) -> Mapping[str, Mapping[Any, Optional[str]]]:
    if tag is None:
        tag = key
    return {
        key: {
            False: None,
            True: tag,
        },
    }


def tags_from_case(spec: Mapping[str, Mapping[Any, Optional[str]]], case: Mapping[str, Any]) -> Iterable[str]:
    for key, value in case.items():
        result = spec[key][value]
        if result is not None:
            yield result
