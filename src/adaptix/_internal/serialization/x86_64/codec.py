from collections.abc import Callable, Iterable
from types import BuiltinFunctionType

from adaptix._internal.code_tools.native_callable import NativeCode
from adaptix._internal.code_tools.x86_64_compiler import X86Compiler
from adaptix._internal.retort.operating_retort import FuncWrapper
from adaptix._internal.serialization.json import StdlibJsonCodec
from adaptix._internal.serialization.number_format import FloatFormatter, get_float_formatter
from adaptix._internal.serialization.perfect_hash import PerfectHash
from adaptix._internal.serialization.plan import describe_model_input, describe_output
from adaptix._internal.serialization.x86_64.input import ModelReader
from adaptix._internal.serialization.x86_64.output import make_generic_writer, make_output_writer
from adaptix._internal.serialization.x86_64.reader import make_decoder
from adaptix._internal.serialization.x86_64.writer import make_encoder


def converter_strings(converter) -> tuple[str, ...]:
    pending, seen, names = [converter], set(), {}
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        if type(value) is str:
            # JSON escaped names use the general string path. A surrogate
            # cannot appear in an unescaped UTF-8 key.
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                continue
            names[value] = None
        elif type(value) is BuiltinFunctionType and isinstance(value.__self__, NativeCode):
            pending.extend(value.__self__.constants)
        elif isinstance(value, FuncWrapper):
            pending.append(value.__call__)
        elif type(value) is tuple:
            pending.extend(value)
    return tuple(names)


class X86JsonCodec:
    def __init__(
        self, *, compiler_factory: Callable[[str], X86Compiler],
        float_formatter_factory: Callable[[], FloatFormatter | None] = get_float_formatter,
    ):
        self.compiler_factory = compiler_factory
        self.fallback = StdlibJsonCodec()
        self.decode_fallback = self.fallback.make_decoder()
        self.decoders = {}
        self.encoders = {}
        self.writer = None
        self.float_formatter_factory = float_formatter_factory

    def make_decoder(self, field_names: Iterable[str] = ()):
        names = tuple(dict.fromkeys(field_names))
        try:
            return self.decoders[names]
        except KeyError:
            pass
        table = PerfectHash.build(names)
        decoder = make_decoder(self.compiler_factory, self.decode_fallback, table)
        self.decoders[names] = decoder
        return decoder

    def get_encoder(self, *, as_bytes: bool):
        try:
            return self.encoders[as_bytes]
        except KeyError:
            pass
        if self.writer is None:
            self.writer = make_generic_writer(self.compiler_factory, self.float_formatter_factory())
        encoder = make_encoder(
            self.compiler_factory,
            self.fallback.encode if as_bytes else self.fallback.encode_str,
            as_bytes=as_bytes,
            routine=self.writer,
        )
        self.encoders[as_bytes] = encoder
        return encoder

    def encode(self, value):
        return self.get_encoder(as_bytes=True)(value)

    def encode_str(self, value):
        return self.get_encoder(as_bytes=False)(value)

    def make_loader(self, loader):
        plan = describe_model_input(loader)
        if plan is not None:
            def fallback(value):
                return loader(self.decode_fallback(value))

            table = PerfectHash.build(plan.name_layout.crown.map)
            model = ModelReader(plan)
            model.key_order = () if table is None else tuple(name for name in table.names if name is not None)
            return make_decoder(
                self.compiler_factory, fallback, table, model=model, decode_scalar=self.decode_fallback,
            )
        decoder = self.make_decoder(converter_strings(loader))
        compiler = self.compiler_factory("json_load")
        parsed = compiler.call(decoder, compiler.data)
        result = compiler.call(loader, parsed)
        return compiler.finish(result).make_callable()

    def make_dumper(self, dumper, *, as_bytes: bool):
        output = describe_output(dumper)
        if output is not None:
            encode = self.fallback.encode if as_bytes else self.fallback.encode_str

            def fallback(value):
                return encode(dumper(value))

            routine = make_output_writer(self.compiler_factory, output, self.float_formatter_factory())
            return make_encoder(
                self.compiler_factory, fallback, as_bytes=as_bytes, routine=routine,
            )
        encoder = self.get_encoder(as_bytes=as_bytes)
        compiler = self.compiler_factory("json_dump")
        dumped = compiler.call(dumper, compiler.data)
        result = compiler.call(encoder, dumped)
        return compiler.finish(result).make_callable()
