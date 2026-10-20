import ctypes
import os
import platform
import sys
import sysconfig
from functools import cache

from adaptix._internal.code_tools.cpython_layout.definitions import CPythonLayout
from adaptix._internal.code_tools.cpython_layout.v3_10 import LAYOUT as CPYTHON_310
from adaptix._internal.code_tools.cpython_layout.v3_11 import LAYOUT as CPYTHON_311
from adaptix._internal.code_tools.cpython_layout.v3_12 import LAYOUT as CPYTHON_312
from adaptix._internal.code_tools.cpython_layout.v3_13 import LAYOUT as CPYTHON_313
from adaptix._internal.code_tools.cpython_layout.v3_14 import LAYOUT as CPYTHON_314
from adaptix._internal.code_tools.cpython_layout.v3_15 import LAYOUT as CPYTHON_315

PRERELEASE_LAYOUT_ENV_VAR = "ADAPTIX_ALLOW_PRERELEASE_LAYOUT"

LAYOUTS = {
    layout.version: layout for layout in (CPYTHON_310, CPYTHON_311, CPYTHON_312, CPYTHON_313, CPYTHON_314, CPYTHON_315)
}


def select_cpython_layout(
    version: tuple[int, int], *, implementation: str, system: str, architecture: str,
    pointer_size: int, special_build: bool, release_level: str = "final",
    allow_prerelease: bool = False,
) -> CPythonLayout | None:
    if (
        implementation != "cpython" or system != "linux" or architecture.lower() not in {"x86_64", "amd64"}
        or pointer_size != 8 or special_build  # noqa: PLR2004
        or (release_level != "final" and not allow_prerelease)
    ):
        return None
    return LAYOUTS.get(version)


def prerelease_layout_allowed() -> bool:
    return os.environ.get(PRERELEASE_LAYOUT_ENV_VAR) == "1"


@cache
def get_cpython_layout() -> CPythonLayout | None:
    release_level = sys.version_info.releaselevel
    layout = select_cpython_layout(
        sys.version_info[:2], implementation=sys.implementation.name, system=sys.platform,
        architecture=platform.machine(),
        pointer_size=ctypes.sizeof(ctypes.c_void_p),
        release_level=release_level,
        allow_prerelease=prerelease_layout_allowed(),
        special_build=(
            any(sysconfig.get_config_var(flag) for flag in ("Py_DEBUG", "Py_TRACE_REFS", "Py_STATS", "Py_GIL_DISABLED"))
            or hasattr(sys, "gettotalrefcount") or hasattr(sys, "_stats_dump")
        ),
    )
    if layout is None or release_level == "final":
        return layout
    # A prerelease may move any structure, so the opt-in is honoured only
    # while every probe still agrees with the running interpreter.
    from adaptix._internal.code_tools.cpython_layout.validation import (  # noqa: PLC0415
        layout_matches_interpreter,
    )
    return layout if layout_matches_interpreter(layout) else None


def require_cpython_layout() -> CPythonLayout:
    layout = get_cpython_layout()
    if layout is None:
        raise RuntimeError("No CPython layout is available for this interpreter build")
    return layout
