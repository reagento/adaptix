# ruff: noqa: T201
# I really want to prevent using typing.get_type_hints(),
# but I found no linters that can check this.
# There is flake8-forbidden-func, but it crashes when trying to check this project.
# I also try bellybutton, however, it recursively scans all directories and then applies glob filter,
# so it takes too long if the project contains tens venvs.
# Finally, this script is a modified version of astpath CLI (this library is used by bellybutton)

import argparse
import os
import sys
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import List

from astpath.search import file_to_xml_ast, find_in_ast


class Rule(ABC):
    @abstractmethod
    def get_patterns(self) -> Iterable[str]:
        pass

    @abstractmethod
    def get_error_msg(self) -> str:
        pass

    @abstractmethod
    def get_exclude_patterns(self) -> Iterable[str]:
        pass


class ImportRule(Rule):
    def __init__(self, module: str, variable: str, error_msg: str, exclude: List[str]):
        self.module = module
        self.variable = variable
        self.error_msg = error_msg
        self.exclude = exclude

    def get_patterns(self) -> Iterable[str]:
        return [
            f".//ImportFrom[@module='{self.module}']/names/*[@name='{self.variable}']",
            f".//Attribute[@attr='{self.variable}']/value/Name[@id='{self.module}']",
        ]

    def get_error_msg(self) -> str:
        return self.error_msg

    def get_exclude_patterns(self) -> Iterable[str]:
        return self.exclude


@dataclass
class RuleMatch:
    file_path: str
    line: int
    rule: Rule


GLOBAL_EXCLUDE = "*_312.py"
RULES = [
    ImportRule(
        module="typing",
        variable="get_type_hints",
        error_msg="Use type_tools.get_all_type_hints() instead of typing.get_type_hints()",
        exclude=["src/adaptix/_internal/type_tools/fundamentals.py"],
    ),
    ImportRule(
        module="_decimal",
        variable="Decimal",
        error_msg='Import Decimal from public module "decimal"',
        exclude=[],
    ),
    ImportRule(
        module="typing",
        variable="get_args",
        error_msg="Use type_tools.get_generic_args() instead of typing.get_args()",
        exclude=["src/adaptix/_internal/type_tools/fundamentals.py"],
    ),
    ImportRule(
        module="typing",
        variable="get_origin",
        error_msg="Use type_tools.strip_alias() instead of typing.get_origin()",
        exclude=["src/adaptix/_internal/type_tools/fundamentals.py"],
    ),
]


def analyze_file(filename: str, rule_matches: List[RuleMatch]) -> None:
    xml_ast = file_to_xml_ast(filename)

    for rule in RULES:
        if any(fnmatch(filename, exclude_pattern) for exclude_pattern in rule.get_exclude_patterns()):
            continue

        for pattern in rule.get_patterns():
            matches_lines = find_in_ast(xml_ast, pattern)
            rule_matches.extend(
                RuleMatch(file_path=filename, line=line, rule=rule)
                for line in matches_lines
            )


def print_rule_matches(rule_matches: Iterable[RuleMatch]):
    messages = [
        (f"{rule_match.file_path}:{rule_match.line}", rule_match.rule.get_error_msg())
        for rule_match in rule_matches
    ]
    max_path_len = max(len(msg[0]) for msg in messages)

    for loc, msg in messages:
        print(loc.ljust(max_path_len + 2), msg)
    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", help="files to lint", nargs="+")
    args = parser.parse_args()

    rule_matches: List[RuleMatch] = []

    for target in args.targets:
        for root, _, filenames in os.walk(target):
            python_filenames = (
                os.path.join(root, filename)  # noqa: PTH118
                for filename in filenames
                if filename.endswith(".py")
            )
            for filename in python_filenames:
                if fnmatch(filename, GLOBAL_EXCLUDE):
                    continue
                analyze_file(filename, rule_matches)

    if rule_matches:
        print_rule_matches(rule_matches)
        sys.exit(1)
    else:
        print("no issues found")


if __name__ == "__main__":
    main()
