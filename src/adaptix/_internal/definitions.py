from enum import Enum


class CodeGenBackend(Enum):
    PYTHON = "python"
    X86_64 = "x86_64"


class DebugTrail(Enum):
    DISABLE = "DISABLE"
    FIRST = "FIRST"
    ALL = "ALL"


class Direction(Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
