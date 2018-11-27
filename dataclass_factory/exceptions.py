from typing import List


class InvalidFieldError(ValueError):
    def __init__(self, message: str, field_path: List[str]):
        super().__init__(message, field_path)
        self.message = message
        self.field_path = field_path

    def _append_path(self, *path: str):
        self.field_path.extend(path)

    def __str__(self):
        path = ", ".join(self.field_path)
        return f"Invalid data at path [{path}]: {self.message}"
