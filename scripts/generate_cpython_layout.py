import argparse
import platform
import shlex
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

CORE_FIELDS = {
    "object_refcount": "offsetof(PyObject, ob_refcnt)",
    "object_type": "offsetof(PyObject, ob_type)",
    "object_size": "sizeof(PyObject)",
    "var_size": "offsetof(PyVarObject, ob_size)",
    "list_items": "offsetof(PyListObject, ob_item)",
    "list_allocated": "offsetof(PyListObject, allocated)",
    "tuple_items": "offsetof(PyTupleObject, ob_item)",
    "set_used": "offsetof(PySetObject, used)",
}

RUNTIME_FIELDS = {
    "type_basic_size": "offsetof(PyTypeObject, tp_basicsize)",
    "type_getattro": "offsetof(PyTypeObject, tp_getattro)",
    "type_flags": "offsetof(PyTypeObject, tp_flags)",
    "type_version": "offsetof(PyTypeObject, tp_version_tag)",
    "type_cached_keys": "offsetof(PyHeapTypeObject, ht_cached_keys)",
    "dict_used": "offsetof(PyDictObject, ma_used)",
    "dict_keys": "offsetof(PyDictObject, ma_keys)",
    "dict_values": "offsetof(PyDictObject, ma_values)",
    "keys_refcount": "offsetof(PyDictKeysObject, dk_refcnt)",
    "keys_index_bytes": "offsetof(PyDictKeysObject, dk_log2_index_bytes)",
    "keys_kind": "offsetof(PyDictKeysObject, dk_kind)",
    "keys_nentries": "offsetof(PyDictKeysObject, dk_nentries)",
    "keys_indices": "offsetof(PyDictKeysObject, dk_indices)",
    "unicode_entry_size": "sizeof(PyDictUnicodeEntry)",
    "unicode_entry_key": "offsetof(PyDictUnicodeEntry, me_key)",
    "unicode_entry_value": "offsetof(PyDictUnicodeEntry, me_value)",
    "general_entry_size": "sizeof(PyDictKeyEntry)",
    "general_entry_key": "offsetof(PyDictKeyEntry, me_key)",
    "general_entry_value": "offsetof(PyDictKeyEntry, me_value)",
    "values_capacity": "offsetof(PyDictValues, capacity)",
    "values_size": "offsetof(PyDictValues, size)",
    "values_valid": "offsetof(PyDictValues, valid)",
    "values_items": "offsetof(PyDictValues, values)",
    "unicode_length": "offsetof(PyASCIIObject, length)",
    "unicode_hash": "offsetof(PyASCIIObject, hash)",
    "unicode_state": "offsetof(PyASCIIObject, state)",
    "unicode_ascii_data": "sizeof(PyASCIIObject)",
    "bytes_data": "offsetof(PyBytesObject, ob_sval)",
    "long_tag": "offsetof(PyLongObject, long_value.lv_tag)",
    "long_digits": "offsetof(PyLongObject, long_value.ob_digit)",
    "set_mask": "offsetof(PySetObject, mask)",
    "set_table": "offsetof(PySetObject, table)",
    "set_entry_size": "sizeof(setentry)",
    "member_descriptor_member": "offsetof(PyMemberDescrObject, d_member)",
    "member_type": "offsetof(PyMemberDef, type)",
    "member_offset": "offsetof(PyMemberDef, offset)",
    "member_flags": "offsetof(PyMemberDef, flags)",
    "function_code": "offsetof(PyFunctionObject, func_code)",
    "function_defaults": "offsetof(PyFunctionObject, func_defaults)",
    "function_kwdefaults": "offsetof(PyFunctionObject, func_kwdefaults)",
    "cell_contents": "offsetof(PyCellObject, ob_ref)",
    "cell_size": "sizeof(PyCellObject)",
    "thread_interpreter": "offsetof(PyThreadState, interp)",
    "thread_eval_breaker": "offsetof(PyThreadState, eval_breaker)",
    "thread_profile": "offsetof(PyThreadState, c_profilefunc)",
    "thread_trace": "offsetof(PyThreadState, c_tracefunc)",
    "interpreter_eval_frame": "offsetof(PyInterpreterState, eval_frame)",
    "datetime_hash": "offsetof(PyDateTime_DateTime, hashcode)",
    "datetime_has_tzinfo": "offsetof(PyDateTime_DateTime, hastzinfo)",
    "datetime_data": "offsetof(PyDateTime_DateTime, data)",
    "datetime_tzinfo": "offsetof(PyDateTime_DateTime, tzinfo)",
    "datetime_naive_size": "sizeof(_PyDateTime_BaseDateTime)",
    "datetime_size": "sizeof(PyDateTime_DateTime)",
    "date_size": "sizeof(PyDateTime_Date)",
    "time_data": "offsetof(PyDateTime_Time, data)",
    "time_tzinfo": "offsetof(PyDateTime_Time, tzinfo)",
    "time_naive_size": "sizeof(_PyDateTime_BaseTime)",
    "time_size": "sizeof(PyDateTime_Time)",
    "timedelta_days": "offsetof(PyDateTime_Delta, days)",
    "timedelta_seconds": "offsetof(PyDateTime_Delta, seconds)",
    "timedelta_microseconds": "offsetof(PyDateTime_Delta, microseconds)",
    "timedelta_size": "sizeof(PyDateTime_Delta)",
    "dictiter_dict": "offsetof(LayoutDictIterator, di_dict)",
    "dictiter_used": "offsetof(LayoutDictIterator, di_used)",
    "dictiter_position": "offsetof(LayoutDictIterator, di_pos)",
    "dictiter_remaining": "offsetof(LayoutDictIterator, len)",
    "abc_negative_cache": "offsetof(LayoutABCData, negative_cache)",
    "abc_invalidation_counter": "offsetof(LayoutABCState, invalidation_counter)",
    "timezone_offset": "offsetof(LayoutTimezone, offset)",
    "timezone_size": "sizeof(LayoutTimezone)",
}

# Private structures from Objects/dictobject.c, Modules/_abc.c and
# Modules/_datetimemodule.c in CPython 3.13-3.15. Runtime probes in the
# corresponding emitters verify these layouts before enabling direct access.
SOURCE_TYPES = """
typedef struct {
    PyObject_HEAD
    PyDictObject *di_dict;
    Py_ssize_t di_used, di_pos;
    PyObject *di_result;
    Py_ssize_t len;
} LayoutDictIterator;
typedef struct {
    PyObject_HEAD
    PyObject *registry, *cache, *negative_cache;
    unsigned long long negative_cache_version;
} LayoutABCData;
typedef struct {
    PyTypeObject *abc_data_type;
    unsigned long long invalidation_counter;
} LayoutABCState;
typedef struct {
    PyObject_HEAD
    PyObject *offset, *name;
} LayoutTimezone;
"""


def collect_offsets(compiler: str) -> dict[str, int]:
    fields = CORE_FIELDS | (RUNTIME_FIELDS if sys.version_info >= (3, 13) else {})
    includes = '#include "Python.h"\n#include <stddef.h>\n#include <stdio.h>\n'
    if sys.version_info >= (3, 13):
        includes += '#include "structmember.h"\n#include "datetime.h"\n#include "internal/pycore_dict.h"\n'
        includes += '#include "internal/pycore_interp.h"\n'
        includes += SOURCE_TYPES
    body = "\n".join(f'printf("{name}=%zu\\n", (size_t)({expression}));' for name, expression in fields.items())
    with tempfile.TemporaryDirectory(prefix="adaptix-layout-") as directory:
        source, executable = Path(directory) / "layout.c", Path(directory) / "layout"
        source.write_text(includes + "int main(void) {\n" + body + "\nreturn 0;\n}\n")
        subprocess.run(  # noqa: S603
            [*shlex.split(compiler), "-DPy_BUILD_CORE", "-I" + sysconfig.get_path("include"),
             str(source), "-o", str(executable)],
            check=True,
        )
        result = subprocess.run([str(executable)], check=True, capture_output=True, text=True)  # noqa: S603
    return {name: int(value) for name, value in (line.split("=") for line in result.stdout.splitlines())}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate offsets using this interpreter's CPython headers")
    parser.add_argument("--compiler", default="cc")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    version = sys.version_info[:2]
    if sys.implementation.name != "cpython" or version not in {(3, 10), (3, 11), (3, 12), (3, 13), (3, 14), (3, 15)}:
        parser.error("Use a supported CPython interpreter (3.10-3.15)")
    if sys.version_info.releaselevel != "final":
        parser.error("Use a final CPython release; prerelease layouts may differ")
    if (
        sys.platform != "linux" or platform.machine().lower() not in {"x86_64", "amd64"}
        or sysconfig.get_config_var("SIZEOF_VOID_P") != 8  # noqa: PLR2004
    ):
        parser.error("These layouts target Linux x86-64")
    if any(sysconfig.get_config_var(flag) for flag in ("Py_DEBUG", "Py_TRACE_REFS", "Py_GIL_DISABLED", "Py_STATS")):
        parser.error("Use a release build with the GIL enabled")
    offsets = collect_offsets(args.compiler)
    text = (
        f"# Generated from CPython {sys.version.split()[0]} headers by scripts/generate_cpython_layout.py.\n"
        "from adaptix._internal.code_tools.cpython_layout.definitions import CPythonLayout\n\n"
        f"LAYOUT = CPythonLayout(\n    version={version!r},\n"
        + "".join(f"    {name}={value},\n" for name, value in offsets.items())
        + ")\n"
    )
    if args.output is None:
        sys.stdout.write(text)
    else:
        args.output.write_text(text)


if __name__ == "__main__":
    main()
