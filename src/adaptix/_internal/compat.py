try:
    from builtins import ExceptionGroup
except ImportError:
    from exceptiongroup import ExceptionGroup  # type: ignore[no-redef]

CompatExceptionGroup = ExceptionGroup
