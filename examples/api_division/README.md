# API division

This example shows how the library can be used in a real project
and illustrates adding custom types support
as well as separating the representation of the same model for external and internal APIs.

The code for the external API contains a lot more validation,
which is useless when data loaded from a trusted source.

For simplicity, `INNER_RECEIPT_FACTORY` and `OUTER_RECEIPT_FACTORY` are contained in one module,
but in a production code, most likely, they should be placed in their [Interface Adapters](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) layer
