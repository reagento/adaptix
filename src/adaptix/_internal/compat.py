try:
    from builtins import ExceptionGroup  # noqa: A004
except ImportError:
    from exceptiongroup import ExceptionGroup  # type: ignore[no-redef]  # noqa: A004

CompatExceptionGroup = ExceptionGroup
