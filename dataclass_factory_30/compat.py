try:
    from typing import NewType
except ImportError:
    try:
        from typing_extensions import NewType
    except ImportError:
        pass
