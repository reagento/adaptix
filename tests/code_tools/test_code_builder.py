from dataclass_factory.code_tools import CodeBuilder


def test_append_lines():
    builder = CodeBuilder()

    builder += "line1"
    builder += """
        line2
        line3
    """

    assert builder.string() == "line1\nline2\nline3"

    builder = CodeBuilder()

    with builder:
        builder += "line1"
        builder += """
            line2
            line3
        """

    assert builder.string() == "    line1\n    line2\n    line3"


def test_first_include():
    builder = CodeBuilder()
    builder <<= "abc"

    assert builder.string() == "abc"


def test_include_lines():
    builder = CodeBuilder()

    builder += "a "
    builder <<= "+ b"
    assert builder.string() == "a + b"

    builder = CodeBuilder()

    builder += "a * "
    builder <<= """
        (
            b + c
        )
    """

    assert builder.string() == "a * (\n    b + c\n)"
