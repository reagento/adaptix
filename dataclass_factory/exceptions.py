from typing import Any, List, Set, Tuple


class ParseError(ValueError):
    pass


class InvalidFieldError(ParseError):
    def __init__(self, message: str, field_path: List[str]):
        super().__init__(message, field_path)
        self.message = message
        self.field_path = field_path

    def _append_path(self, *path: str):
        self.field_path.extend(path)

    def __str__(self):
        path = ", ".join(self.field_path)
        return f"Invalid data at path [{path}]: {self.message}"


class UnknownFieldsError(ParseError):
    def __init__(self, message: str, fields: Set[str]):
        super().__init__(message, fields)
        self.message = message
        self.fields = fields

    def __str__(self):
        return f"Unknown fields found {self.fields}: {self.message}"


class UnionParseError(ParseError):
    def __init__(self, message: str, suberrors: List[Tuple[Any, Exception]]):
        super().__init__(message, suberrors)
        self.message = message
        self.suberrors = suberrors

    def __str__(self):
        res = f"{self.message}\nSuberrors:\n"
        for key, error in self.suberrors:
            res += f"  * {key}: {error}\n"
        return res
