import importlib
from pkgutil import walk_packages

import pytest
from tests_helpers import full_match

import adaptix
from adaptix._internal.feature_requirement import HAS_SQLALCHEMY_PKG


def test_all_modules_are_importable():
    for module_info in walk_packages(adaptix.__path__, f"{adaptix.__name__}."):
        if (
            module_info.name.startswith(
                ("adaptix._internal.integrations.sqlalchemy.", "adaptix.integrations.sqlalchemy"),
            )
            and not HAS_SQLALCHEMY_PKG
        ):
            with pytest.raises(ModuleNotFoundError, match=full_match("No module named 'sqlalchemy'")):
                importlib.import_module(module_info.name)
        else:
            importlib.import_module(module_info.name)
