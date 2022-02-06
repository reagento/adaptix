import contextlib
from collections import ChainMap
from textwrap import dedent
from typing import Mapping, List, Sequence


class CodeBuilder:
    def __init__(self, indent_delta: int = 4):
        self._lines: List[str] = []
        self._cur_indent = 0
        self._indent_delta = indent_delta

    @property
    def indent_delta(self):
        return self._indent_delta

    @property
    def lines(self) -> Sequence[str]:
        return self._lines

    def _add_string(self, line_or_text: str):
        if "\n" in line_or_text:
            lines = dedent(line_or_text).strip("\n").split("\n")
        else:
            lines = [line_or_text]

        indent = " " * self._cur_indent
        self._lines.extend(
            indent + line
            for line in lines
        )

    def __call__(self, line_or_text: str):
        self._add_string(
            line_or_text,
        )
        return self

    def __iadd__(self, line_or_text: str):
        self(line_or_text)
        return self

    def empty_line(self):
        self("")
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

    def extend(self, other: "CodeBuilder"):
        for line in other.lines:
            self(line)
        return self

    def string(self) -> str:
        return "\n".join(self.lines)

    def get_context(self) -> Mapping[str, str]:
        return ChainMap(*reversed(self._ctx_list))  # type: ignore
