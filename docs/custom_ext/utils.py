import hashlib
from pathlib import Path


def file_ascii_hash(file_path: str) -> str:
    return hashlib.md5(Path(file_path).read_bytes(), usedforsecurity=False).hexdigest()
