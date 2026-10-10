import ctypes

import pytest

from adaptix._internal.serialization.number_format import get_float_formatter


@pytest.mark.parametrize("missing", ["library", "symbol"])
def test_missing_system_formatter_uses_fallback(monkeypatch, missing):
    original = ctypes.CDLL

    def load(name, *args, **kwargs):
        if name == "libstdc++.so.6":
            if missing == "library":
                raise OSError("unavailable")
            return object()
        return original(name, *args, **kwargs)

    monkeypatch.setattr(ctypes, "CDLL", load)
    assert get_float_formatter.__wrapped__() is None
