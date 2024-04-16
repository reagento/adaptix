import importlib
from pkgutil import walk_packages

import adaptix


def test_all_modules_is_importable():
    for module_info in walk_packages(adaptix.__path__, f"{adaptix.__name__}."):
        importlib.import_module(module_info.name)
