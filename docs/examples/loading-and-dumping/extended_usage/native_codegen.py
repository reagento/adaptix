from dataclasses import dataclass

from adaptix import CodeGenBackend, Retort


@dataclass
class Book:
    title: str
    pages: int


def main():
    retort = Retort(codegen_backend=CodeGenBackend.X86_64)
    book = retort.load({"title": "Example", "pages": 120}, Book)
    assert book == Book("Example", 120)
    assert retort.dump(book) == {"title": "Example", "pages": 120}


if __name__ == "__main__":
    main()
