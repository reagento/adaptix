import importlib
from pathlib import Path

import pytest

from adaptix._internal.feature_requirement import HAS_PY_311, HAS_SUPPORTED_PYDANTIC_PKG

REPO_ROOT = Path(__file__).parent.parent
DOCS_EXAMPLES_ROOT = REPO_ROOT / "docs" / "examples"
EXCLUDE = ["__init__.py"]
GLOB = "*.py"


def pytest_generate_tests(metafunc):
    if "import_path" not in metafunc.fixturenames:
        return

    paths_to_test = [
        sub_path
        for sub_path in DOCS_EXAMPLES_ROOT.rglob(GLOB)
        if sub_path.name not in EXCLUDE and not sub_path.is_dir()
    ]
    metafunc.parametrize(
        ["import_path", "case_id"],
        [
            pytest.param(
                ".".join((path_to_test.parent / path_to_test.stem).relative_to(REPO_ROOT).parts),
                str((path_to_test.parent / path_to_test.stem).relative_to(DOCS_EXAMPLES_ROOT).as_posix()),
                id=str((path_to_test.parent / path_to_test.stem).relative_to(DOCS_EXAMPLES_ROOT).as_posix()),
            )
            for path_to_test in paths_to_test
        ],
    )


CASES_REQUIREMENTS = {
    "loading-and-dumping/tutorial/unexpected_error": HAS_PY_311,
    "reference/integrations/native_pydantic": HAS_SUPPORTED_PYDANTIC_PKG,
}


def test_example(import_path: str, case_id: str):
    if case_id in CASES_REQUIREMENTS:
        requirement = CASES_REQUIREMENTS[case_id]
        if not requirement:
            pytest.skip(requirement.fail_reason)

    pytest.register_assert_rewrite(import_path)
    importlib.import_module(import_path)
