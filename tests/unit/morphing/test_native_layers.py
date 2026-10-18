import ast
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import adaptix


def test_python_backend_does_not_import_instruction_emitters():
    script = dedent("""\
        import importlib.abc
        import sys

        class BlockMachineCode(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path, target=None):
                if fullname.startswith((
                    "adaptix._internal.morphing.native.x86_64",
                    "adaptix._internal.code_tools.x86_64_",
                    "adaptix._internal.code_tools.native_access",
                )):
                    raise AssertionError(f"Python generation imported {fullname}")

        sys.meta_path.insert(0, BlockMachineCode())
        from dataclasses import dataclass
        from datetime import date, datetime
        from decimal import Decimal
        from enum import Enum
        from typing import Literal, Union
        from uuid import UUID

        from adaptix import Retort

        class Choice(Enum):
            FIRST = "first"

        @dataclass
        class Model:
            count: int
            values: list[Union[int, str]]

        retort = Retort()
        cases = [
            (Model, {"count": 1, "values": [2, "three"]}),
            (list[Union[int, str, None]], [1, "two", None]),
            (tuple[int, str], [1, "two"]),
            (dict[str, int], {"a": 1}),
            (set[int], [1, 2]),
            (Union[Decimal, None], "1.25"),
            (Literal["first", "second"], "first"),
            (Choice, "first"),
            (date, "2026-10-10"),
            (datetime, "2026-10-10T12:30:00"),
            (bytes, "YQ=="),
            (UUID, "12345678-1234-5678-1234-567812345678"),
        ]
        for tp, data in cases:
            value = retort.load(data, tp)
            assert retort.load(retort.dump(value, tp), tp) == value
        """)
    subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)  # noqa: S603


def test_instruction_tools_do_not_depend_on_morphing_or_providers():
    directory = Path(adaptix.__file__).parent / "_internal" / "code_tools"
    for path in directory.glob("*.py"):
        if not path.name.startswith(("native_", "x86_64_")):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                assert not node.module.startswith((
                    "adaptix._internal.morphing", "adaptix._internal.provider", "adaptix._internal.retort",
                )), (path.name, node.module)


def test_field_ir_does_not_depend_on_instruction_emitters():
    directory = Path(adaptix.__file__).parent / "_internal" / "morphing" / "native"
    for name in ("bytecodes.py", "model_ir.py", "optimizer.py"):
        for node in ast.walk(ast.parse((directory / name).read_text())):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                assert not node.module.startswith((
                    "adaptix._internal.code_tools", "adaptix._internal.morphing.native.x86_64",
                )), (name, node.module)
