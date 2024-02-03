try:
    from builtins import ExceptionGroup  # noqa: A004
except ImportError:
    from exceptiongroup import ExceptionGroup  # type: ignore[no-redef]  # noqa: A004

CompatExceptionGroup = ExceptionGroup


try:
    from ast import unparse
except ImportError:
    from astunparse import unparse  # type: ignore[no-redef]

compat_ast_unparse = unparse
