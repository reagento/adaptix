import platform
import sys
import sysconfig
from collections.abc import Mapping


def benchmark_env_spec() -> dict[str, str]:
    return {
        "py": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "py_impl": sys.implementation.name,
        "os": sys.platform,
        "arch": platform.machine().lower(),
        "gil": "disabled" if sysconfig.get_config_var("Py_GIL_DISABLED") else "enabled",
    }


def skip_native(env_spec: Mapping[str, str]) -> bool:
    return (
        env_spec["py_impl"] != "cpython"
        or env_spec["os"] != "linux"
        or env_spec["arch"] not in {"x86_64", "amd64"}
        or env_spec["gil"] != "enabled"
    )
