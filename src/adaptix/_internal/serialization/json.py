import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol

JsonInput = str | bytes | bytearray


class JsonCodec(Protocol):
    def make_decoder(self, field_names: Iterable[str] = ()) -> Callable[[JsonInput], Any]: ...

    def encode(self, value: Any) -> bytes: ...

    def encode_str(self, value: Any) -> str: ...

    def make_loader(self, loader: Callable) -> Callable: ...

    def make_dumper(self, dumper: Callable, *, as_bytes: bool) -> Callable: ...


def reject_constant(value: str):
    raise ValueError(f"Invalid JSON constant: {value}")


@dataclass(frozen=True)
class StdlibJsonCodec:
    def make_decoder(self, field_names: Iterable[str] = ()) -> Callable[[JsonInput], Any]:
        decoder = json.JSONDecoder(parse_constant=reject_constant)

        def decode(data: JsonInput):
            if isinstance(data, (bytes, bytearray)):
                data = data.decode(json.detect_encoding(data))
            if not isinstance(data, str):
                raise TypeError("JSON input must be str, bytes or bytearray")
            return decoder.decode(data)

        return decode

    def encode(self, value: Any) -> bytes:
        return self.encode_str(value).encode("utf-8")

    def encode_str(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))

    def make_loader(self, loader: Callable) -> Callable:
        decode = self.make_decoder()

        def load(data: JsonInput):
            return loader(decode(data))

        return load

    def make_dumper(self, dumper: Callable, *, as_bytes: bool) -> Callable:
        encode = self.encode if as_bytes else self.encode_str

        def dump(data):
            return encode(dumper(data))

        return dump
