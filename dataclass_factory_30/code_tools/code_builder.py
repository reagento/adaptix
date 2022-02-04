import contextlib
from collections import ChainMap
from string import Template
from textwrap import dedent
from typing import Optional, Mapping, List, Sequence


class CodeBuilder:
    def __init__(
        self,
        ctx: Optional[Mapping[str, str]] = None,
        indent_delta: int = 4
    ):
        self._lines: List[str] = []
        self._cur_indent = 0
        self._indent_delta = indent_delta
        self._ctx_list: List[Mapping[str, str]] = [] if ctx is None else [ctx]

    @property
    def indent_delta(self):
        return self._indent_delta

    @property
    def lines(self) -> Sequence[str]:
        return self._lines

    def _add_string(self, line_or_text: str, processor):
        if "\n" in line_or_text:
            lines = dedent(line_or_text).strip("\n").split("\n")
        else:
            lines = [line_or_text]

        indent = " " * self._cur_indent
        self._lines.extend(
            indent + processor(line)
            for line in lines
        )

    def __call__(self, line_or_text: str, **kwargs: str):
        self._add_string(
            line_or_text,
            lambda line: self._process_line(line, kwargs)
        )
        return self

    def __iadd__(self, line_or_text: str):
        self(line_or_text)
        return self

    def add_raw(self, line_or_text: str):
        self._add_string(
            line_or_text,
            lambda line: line
        )
        return self

    def empty_line(self):
        self.add_raw("")
        return self

    @contextlib.contextmanager
    def indent(self, indent_delta: int):
        self._cur_indent += indent_delta
        yield
        self._cur_indent -= indent_delta

    def __enter__(self):
        self._cur_indent += self._indent_delta

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cur_indent -= self._indent_delta

    def _process_line(self, line: str, local_ctx: Mapping[str, str]) -> str:
        template = Template(line)
        chain_map = ChainMap(local_ctx, *reversed(self._ctx_list))  # type: ignore
        return template.substitute(chain_map)

    @contextlib.contextmanager
    def context(self, **kwargs: str):
        self._ctx_list.append(kwargs)
        yield
        self._ctx_list.pop(-1)

    def extend(self, other: "CodeBuilder"):
        for line in other.lines:
            self.add_raw(line)
        return self

    def string(self) -> str:
        return "\n".join(self.lines)

    def get_context(self) -> Mapping[str, str]:
        return ChainMap(*reversed(self._ctx_list))  # type: ignore

    def fmt(self, line: str, **kwargs: str) -> str:
        """Format line using context of CodeBuilder.
        Does not affect on builder itself
        """
        return self._process_line(line, kwargs)
