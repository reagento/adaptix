import ctypes
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

LAYOUTS = {
    layout.version: layout for layout in (CPYTHON_310, CPYTHON_311, CPYTHON_312, CPYTHON_313, CPYTHON_314, CPYTHON_315)
}


def select_cpython_layout(
    version: tuple[int, int], *, implementation: str, system: str, architecture: str,
    pointer_size: int, special_build: bool, release_level: str = "final",
) -> CPythonLayout | None:
    if (
        implementation != "cpython" or system != "linux" or architecture.lower() not in {"x86_64", "amd64"}
        or pointer_size != 8 or special_build or release_level != "final"  # noqa: PLR2004
    ):
        return None
    return LAYOUTS.get(version)


@cache
def get_cpython_layout() -> CPythonLayout | None:
    return select_cpython_layout(
        sys.version_info[:2], implementation=sys.implementation.name, system=sys.platform,
        architecture=platform.machine(),
        pointer_size=ctypes.sizeof(ctypes.c_void_p),
        release_level=sys.version_info.releaselevel,
        special_build=(
            any(sysconfig.get_config_var(flag) for flag in ("Py_DEBUG", "Py_TRACE_REFS", "Py_STATS", "Py_GIL_DISABLED"))
            or hasattr(sys, "gettotalrefcount") or hasattr(sys, "_stats_dump")
        ),
    )


def require_cpython_layout() -> CPythonLayout:
    layout = get_cpython_layout()
    if layout is None:
        raise RuntimeError("No CPython layout is available for this interpreter build")
    return layout
