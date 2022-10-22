import contextlib
from textwrap import dedent
from typing import Iterable, List, Sequence


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
        return self._lines.copy()

    def _extract_lines(self, line_or_text: str) -> Iterable[str]:
        if "\n" in line_or_text:
            return dedent(line_or_text).strip("\n").split("\n")
        return [line_or_text]

    def _add_indenting_lines(self, lines: Iterable[str]):
        indent = " " * self._cur_indent
        self._lines.extend(
            indent + line
            for line in lines
        )

    def __call__(self, line_or_text: str) -> "CodeBuilder":
        """Append lines to builder"""
        lines = self._extract_lines(line_or_text)
        self._add_indenting_lines(lines)
        return self

    __add__ = __call__
    __iadd__ = __call__

    def include(self, line_or_text: str) -> "CodeBuilder":
        """Add first line of input text to last line of builder and append other lines"""
        first_line, *other_lines = self._extract_lines(line_or_text)

        if self._lines:
            self._lines[-1] += first_line
        else:
            self._lines.append(first_line)
        self._add_indenting_lines(other_lines)
        return self

    __lshift__ = include
    __ilshift__ = include

    def empty_line(self):
        self("")
        return self

    @contextlib.contextmanager
    def indent(self, indent_delta: int):
        self._cur_indent += indent_delta
        try:
            yield
        finally:
            self._cur_indent -= indent_delta

    def __enter__(self):
        self._cur_indent += self._indent_delta

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cur_indent -= self._indent_delta

    def extend(self, other: "CodeBuilder"):
        self._add_indenting_lines(other.lines)
        return self

    def string(self) -> str:
        return "\n".join(self.lines)
