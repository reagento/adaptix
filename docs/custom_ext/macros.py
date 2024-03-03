from abc import ABC, abstractmethod
from textwrap import dedent, indent

from docutils.statemachine import StringList
from sphinx.util import docutils
from sphinx.util.docutils import SphinxDirective

from .utils import file_ascii_hash


class SphinxMacroDirective(SphinxDirective, ABC):
    @abstractmethod
    def generate_string(self) -> str:
        ...

    def run(self):
        content = self.generate_string()
        rst = StringList(content.split("\n"), source="fake.rst")
        node = docutils.nodes.paragraph()
        self.state.nested_parse(rst, 0, node)
        return node.children


class CustomNonGuaranteedBehavior(SphinxMacroDirective):
    required_arguments = 0
    has_content = True

    def generate_string(self) -> str:
        result = dedent(
            """
            .. admonition:: Non-guaranteed behavior
              :class: caution

            """,
        )
        content = indent(
            "\n".join(self.content),
            "  ",
        )
        return result + content


def setup(app):
    app.add_directive("custom-non-guaranteed-behavior", CustomNonGuaranteedBehavior)

    return {
        "version": file_ascii_hash(__file__),
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
