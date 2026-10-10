from typing import Any, TypeVar

from adaptix._internal.common import TypeHint
from adaptix._internal.morphing.facade.retort import Retort
from adaptix._internal.serialization.json import JsonCodec, JsonInput, StdlibJsonCodec

T = TypeVar("T")


class JsonRetort:
    def __init__(self, retort: Retort | None = None, *, codec: JsonCodec | None = None):
        self.retort = Retort() if retort is None else retort
        if codec is None:
            factory = getattr(self.retort.native_codegen, "make_json_codec", None)
            codec = StdlibJsonCodec() if factory is None else factory()
        self.codec = codec
        self.loaders = {}
        self.dumpers = {}

    def get_loader(self, tp: type[T]):
        try:
            return self.loaders[tp]
        except KeyError:
            pass
        load = self.codec.make_loader(self.retort.get_loader(tp))
        self.loaders[tp] = load
        return load

    def get_dumper(self, tp: type[T], *, as_bytes: bool = True):
        key = (tp, as_bytes)
        try:
            return self.dumpers[key]
        except KeyError:
            pass
        dump = self.codec.make_dumper(self.retort.get_dumper(tp), as_bytes=as_bytes)
        self.dumpers[key] = dump
        return dump

    def load(self, data: JsonInput, tp: type[T]) -> T:
        return self.get_loader(tp)(data)

    def dump(self, value: Any, tp: TypeHint | None = None, *, as_bytes: bool = True) -> bytes | str:
        if tp is None:
            return (self.codec.encode if as_bytes else self.codec.encode_str)(self.retort.dump(value))
        return self.get_dumper(tp, as_bytes=as_bytes)(value)
