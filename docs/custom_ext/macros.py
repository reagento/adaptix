import tomllib
from abc import ABC, abstractmethod
from pathlib import Path
from textwrap import dedent, indent
from typing import Iterable

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


def directive(header: str, contents: Iterable[str] = ()) -> str:
    return dedent(header) + "\n" + "\n".join(indent(dedent(content), "   ") for content in contents)


class CustomNonGuaranteedBehavior(SphinxMacroDirective):
    required_arguments = 0
    has_content = True

    def generate_string(self) -> str:
        return directive(
            """
                .. admonition:: Non-guaranteed behavior
                   :class: caution
            """,
            self.content,
        )


ADAPTIX_PYPROJECT = tomllib.loads(Path(__file__).parent.parent.parent.joinpath("pyproject.toml").read_text())


class CustomAdaptixExtrasTable(SphinxMacroDirective):
    required_arguments = 0
    has_content = False

    def generate_string(self) -> str:
        return directive(
            """
                .. list-table::
                   :header-rows: 1
            """,
            [
                """
                    * - Extras
                      - Versions bound
                """,
                *[
                    f"""
                    * - ``{extras}``
                      - ``{'; '.join(deps)}``
                    """
                    for extras, deps in ADAPTIX_PYPROJECT["project"]["optional-dependencies"].items()
                ],
            ],
        )


def setup(app):
    app.add_directive("custom-non-guaranteed-behavior", CustomNonGuaranteedBehavior)
    app.add_directive("custom-adaptix-extras-table", CustomAdaptixExtrasTable)

    return {
        "version": file_ascii_hash(__file__),
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
