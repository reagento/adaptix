import importlib
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional

import pytest
from tests_helpers.misc import AndRequirement

from adaptix._internal.feature_requirement import (
    HAS_PY_311,
    HAS_PY_312,
    HAS_SUPPORTED_MSGSPEC_PKG,
    HAS_SUPPORTED_PYDANTIC_PKG,
    HAS_SUPPORTED_SQLALCHEMY_PKG,
    HAS_TYPED_DICT_REQUIRED,
    Requirement,
)

REPO_ROOT = Path(__file__).parent.parent
DOCS_EXAMPLES_ROOT = REPO_ROOT / "docs" / "examples"
EXCLUDE = ["**/__init__.py", "**/helpers.py", "why_not_pydantic/*benchmark*"]
GLOB = "*.py"


def pytest_generate_tests(metafunc):
    if "import_path" not in metafunc.fixturenames:
        return

    paths_to_test = [
        sub_path
        for sub_path in DOCS_EXAMPLES_ROOT.rglob(GLOB)
        if not any(fnmatch(sub_path.relative_to(DOCS_EXAMPLES_ROOT).as_posix(), glob) for glob in EXCLUDE)
    ]
    parameter_sets = [
        pytest.param(
            ".".join((path_to_test.parent / path_to_test.stem).relative_to(REPO_ROOT).parts),
            str((path_to_test.parent / path_to_test.stem).relative_to(DOCS_EXAMPLES_ROOT).as_posix()),
            id=str((path_to_test.parent / path_to_test.stem).relative_to(DOCS_EXAMPLES_ROOT).as_posix()),
        )
        for path_to_test in paths_to_test
    ]
    for param_set in parameter_sets:
        pytest.register_assert_rewrite(param_set.values[0])
    metafunc.parametrize(["import_path", "case_id"], parameter_sets)


GLOB_REQUIREMENTS = {
    "loading-and-dumping/tutorial/unexpected_error": HAS_PY_311,
    "reference/integrations/native_pydantic": HAS_SUPPORTED_PYDANTIC_PKG,
    "loading-and-dumping/extended_usage/private_fields_including_no_rename_pydantic": HAS_SUPPORTED_PYDANTIC_PKG,
    "loading-and-dumping/extended_usage/private_fields_including_pydantic": HAS_SUPPORTED_PYDANTIC_PKG,
    "loading-and-dumping/extended_usage/private_fields_skipping_pydantic": HAS_SUPPORTED_PYDANTIC_PKG,
    "loading-and-dumping/extended_usage/detecting_absense_of_a_field/typed_dict": HAS_TYPED_DICT_REQUIRED,
    "reference/integrations/sqlalchemy_json/*": HAS_SUPPORTED_SQLALCHEMY_PKG,
    "conversion/tutorial/tldr": HAS_SUPPORTED_SQLALCHEMY_PKG,
    "why_not_pydantic/instantiating_penalty*": AndRequirement(HAS_PY_312, HAS_SUPPORTED_PYDANTIC_PKG),
    "why_not_pydantic/*": HAS_SUPPORTED_PYDANTIC_PKG,
    "reference/integrations/native_msgspec": HAS_SUPPORTED_MSGSPEC_PKG,
}


def _find_requirement(case_id: str) -> Optional[Requirement]:
    for glob, requirement in GLOB_REQUIREMENTS.items():
        if fnmatch(case_id, glob):
            return requirement
    return None


def test_example(import_path: str, case_id: str):
    requirement = _find_requirement(case_id)
    if requirement is not None and not requirement:
        pytest.skip(requirement.fail_reason)

    importlib.import_module(import_path)
