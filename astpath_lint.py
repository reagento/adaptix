# I really want to prevent using typing.get_type_hints(),
# but I found no linters that can check this.
# There is flake8-forbidden-func, but it crashes when trying to check this project.
# I also try bellybutton, however, it recursively scans all directories and then applies glob filter,
# so it takes too long if the project contains tens venvs.
# Finally, this script is a modified version of astpath CLI (this library is used by bellybutton)

import os
import argparse
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Iterable, List

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


RULES = [
    ImportRule(
        module='typing',
        variable='get_type_hints',
        error_msg='Use type_tools.get_all_type_hints() instead of typing.get_type_hints()',
        exclude=['src/_dataclass_factory/type_tools/basic_utils.py'],
    ),
]


def analyze_file(filename: str, rule_matches: List[RuleMatch]) -> None:
    xml_ast = file_to_xml_ast(filename)

    for rule in RULES:
        if any(fnmatch(filename, exclude_pattern) for exclude_pattern in rule.get_exclude_patterns()):
            continue

        for pattern in rule.get_patterns():
            matches_lines = find_in_ast(xml_ast, pattern)

            for line in matches_lines:
                rule_matches.append(
                    RuleMatch(file_path=filename, line=line, rule=rule)
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('targets', help="files to lint", nargs='+', )
    args = parser.parse_args()

    rule_matches: List[RuleMatch] = []

    for target in args.targets:
        for root, _, filenames in os.walk(target):
            python_filenames = (
                os.path.join(root, filename)
                for filename in filenames
                if filename.endswith(".py")
            )
            for filename in python_filenames:
                analyze_file(filename, rule_matches)

    if rule_matches:
        messages = [
            (f"{rule_match.file_path}:{rule_match.line}", rule_match.rule.get_error_msg())
            for rule_match in rule_matches
        ]
        max_path_len = max(len(msg[0]) for msg in messages)

        for loc, msg in messages:
            print(loc.ljust(max_path_len + 2), msg)
        print()
        sys.exit(1)
    else:
        print("no issues found")


if __name__ == "__main__":
    main()
