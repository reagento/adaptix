import json
from textwrap import dedent
from typing import Dict
from zipfile import ZipFile

import plotly
from docutils import nodes
from docutils.statemachine import StringList
from sphinx.util import docutils
from sphinx.util.docutils import SphinxDirective

from benchmarks.bench_nexus import BENCHMARK_HUBS, KEY_TO_HUB, RELEASE_DATA, Renderer, pyperf_bench_to_measure

from .utils import file_ascii_hash


class CustomBenchChart(SphinxDirective):
    required_arguments = 1

    def get_html(self, hub_key: str) -> str:
        hub_description = KEY_TO_HUB[hub_key]
        renderer = Renderer()
        light_html = plotly.offline.plot(
            renderer.render_hub_from_release(hub_description, Renderer.LIGHT_COLOR_SCHEME),
            config={"displaylogo": False},
            include_plotlyjs="cdn",
            output_type="div",
        )
        dark_html = plotly.offline.plot(
            renderer.render_hub_from_release(hub_description, Renderer.DARK_COLOR_SCHEME),
            config={"displaylogo": False},
            include_plotlyjs="cdn",
            output_type="div",
        )
        return f'<div class="only-light">{light_html}</div><div class="only-dark">{dark_html}</div>'

    def run(self):
        plot_html = self.get_html(self.arguments[0])
        raw_node = nodes.raw("", plot_html, format="html")
        raw_node.source, raw_node.line = self.state_machine.get_source_and_line(self.lineno)
        return [
            raw_node,
        ]


class CustomBenchUsedDistributions(SphinxDirective):
    required_arguments = 0

    def get_list_table(self) -> str:
        distributions: Dict[str, str] = {}

        for hub_description in BENCHMARK_HUBS:
            with ZipFile(RELEASE_DATA / f"{hub_description.key}.zip") as release_zip:
                index = json.loads(release_zip.read("index.json"))
                for file_list in index["env_files"].values():
                    for file in file_list:
                        distributions.update(
                            pyperf_bench_to_measure(release_zip.read(file)).distributions,
                        )

        result = dedent(
            """
            .. list-table::
               :header-rows: 1

               * - Library
                 - Used version
                 - Last version
            """,
        )
        for dist in sorted(distributions.keys()):
            version = distributions[dist]
            result += dedent(
                f"""
                   * - `{dist} <https://pypi.org/project/{dist}/>`_
                     - ``{version}``
                     - .. image:: https://img.shields.io/pypi/v/{dist}?logo=pypi&label=%20&color=white&style=flat
                          :target: https://pypi.org/project/{dist}/
                          :class: only-light
                       .. image:: https://img.shields.io/pypi/v/{dist}?logo=pypi&label=%20&color=%23242424&style=flat
                          :target: https://pypi.org/project/{dist}/
                          :class: only-dark
                """,
            ).replace("\n", "\n   ")
        return result

    def run(self):
        list_table = self.get_list_table()
        rst = StringList(list_table.split("\n"), source="fake.rst")
        node = docutils.nodes.paragraph()
        self.state.nested_parse(rst, 0, node)
        return node.children


def setup(app):
    app.add_directive("custom-bench-chart", CustomBenchChart)
    app.add_directive("custom-bench-used-distributions", CustomBenchUsedDistributions)

    return {
        "version": file_ascii_hash(__file__),
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
