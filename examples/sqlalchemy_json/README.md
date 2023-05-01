# SQLAlchemy JSON

This example shows how to use Adaptix with [SQLAlchemy](https://www.sqlalchemy.org/)
to store JSON in a relational database.

Adaptix transparently converts JSON to desired dataclass and vice versa,
your SQLAlchemy models contain already transmuted data.

Be careful persisting JSON in relational databases.
There are a few appropriate use cases for this.
