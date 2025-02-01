import re
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from contextlib import AbstractContextManager, contextmanager
from re import RegexFlag


class TextSliceWriter(AbstractContextManager[None]):
    @abstractmethod
    def write(self, text: str, /) -> None:
        ...


class LinesWriter(TextSliceWriter):
    __slots__ = ("_new_line_replacer", "_slices")

    def __init__(self, start_indent: str = ""):
        self._slices: list[str] = []
        self._new_line_replacer = f"\n{start_indent}"

    def __enter__(self) -> None:
        self._new_line_replacer += "    "

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._new_line_replacer = self._new_line_replacer[:-4]

    def write(self, text: str) -> None:
        self._slices.append(text.replace("\n", self._new_line_replacer))

    def make_string(self) -> str:
        return "\n".join(self._slices)


class OneLineWriter(LinesWriter):
    def make_string(self) -> str:
        return "".join(self._slices)


@contextmanager
def at_one_line(writer: TextSliceWriter):
    sub_writer = OneLineWriter()
    yield sub_writer
    writer.write(sub_writer.make_string())


class Statement(ABC):
    @abstractmethod
    def write_lines(self, writer: TextSliceWriter) -> None:
        ...


class Expression(Statement, ABC):
    pass


class ConcatStatements(Statement):
    def __init__(self, elements: Iterable[Statement]):
        self._elements = elements

    def write_lines(self, writer: TextSliceWriter) -> None:
        for stmt in self._elements:
            stmt.write_lines(writer)


def statements(*elements: Statement) -> ConcatStatements:
    return ConcatStatements(elements)


class RawStatement(Statement):
    def __init__(self, text: str):
        self._text = text

    def write_lines(self, writer: TextSliceWriter) -> None:
        writer.write(self._text)


class RawExpr(RawStatement, Expression):
    pass


class _TemplatedStatement(Statement):
    def __init__(self, template: str, **stmts: Statement):
        self._template = template
        self._name_to_stmt = stmts

    _PLACEHOLDER_REGEX = re.compile(r"<\w+>", RegexFlag.MULTILINE)
    _INDENT_REGEX = re.compile(r"^\s*", RegexFlag.MULTILINE)

    def _format_template(self) -> str:
        return self._PLACEHOLDER_REGEX.sub(self._replace_placeholder, self._template)

    def _replace_placeholder(self, match: re.Match[str]) -> str:
        stmt = self._name_to_stmt[match.group(0)]
        start_idx = match.string.rfind("\n", 0, match.pos)
        indent_match = self._INDENT_REGEX.search(match.string, start_idx)
        if indent_match is None:
            raise ValueError

        writer = LinesWriter(indent_match.group(0))
        stmt.write_lines(writer)
        return writer.make_string()

    def write_lines(self, writer: TextSliceWriter) -> None:
        writer.write(self._format_template())


class CodeBlock(_TemplatedStatement):
    EMPTY_LINE: Statement = RawStatement("")
    PASS: Statement = RawStatement("pass")


class CodeExpr(_TemplatedStatement, Expression):
    def __init__(self, template: str, **exprs: Expression):
        super().__init__(template, **exprs)


class DictItem(ABC):
    @abstractmethod
    def write_item_line(self, sub_writer: TextSliceWriter) -> None:
        ...


class MappingUnpack(DictItem):
    def __init__(self, expr: Expression):
        self._expr = expr

    def write_item_line(self, sub_writer: TextSliceWriter) -> None:
        sub_writer.write("**")
        self._expr.write_lines(sub_writer)


class DictKeyValue(DictItem):
    def __init__(self, key: Expression, value: Expression):
        self._key = key
        self._value = value

    def write_item_line(self, sub_writer: TextSliceWriter) -> None:
        self._key.write_lines(sub_writer)
        sub_writer.write(": ")
        self._value.write_lines(sub_writer)
        sub_writer.write(",")


class DictLiteral(Expression):
    def __init__(self, items: Iterable[DictItem]):
        self._items = items

    def write_lines(self, writer: TextSliceWriter) -> None:
        writer.write("{")
        with writer:
            for item in self._items:
                with at_one_line(writer) as sub_writer:
                    item.write_item_line(sub_writer)
        writer.write("}")


class ListLiteral(Expression):
    def __init__(self, items: Sequence[Expression]):
        self._items = items

    def write_lines(self, writer: TextSliceWriter) -> None:
        writer.write("[")
        with writer:
            for item in self._items:
                with at_one_line(writer) as sub_writer:
                    item.write_lines(sub_writer)
                    sub_writer.write(",")
        writer.write("]")


class StringLiteral(Expression):
    def __init__(self, text: str):
        self._text = text

    def write_lines(self, writer: TextSliceWriter) -> None:
        writer.write(repr(self._text))


class TryExcept(Statement):
    def __init__(self, try_: Statement, excepts: Iterable[tuple[Expression, Statement]], else_: Statement):
        self._try = try_
        self._excepts = excepts
        self._else = else_

    def write_lines(self, writer: TextSliceWriter) -> None:
        if not self._excepts:
            self._try.write_lines(writer)
            if self._else != CodeBlock.PASS:
                self._else.write_lines(writer)
            return

        writer.write("try:")
        with writer:
            self._try.write_lines(writer)

        for catching, handling in self._excepts:
            CodeBlock(
                """
                except <catching>:
                    <handling>
                """,
                catching=catching,
                handling=handling,
            ).write_lines(
                writer,
            )

        if self._else != CodeBlock.PASS:
            writer.write("else:")
            with writer:
                self._else.write_lines(writer)
