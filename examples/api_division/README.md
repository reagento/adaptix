# API division

An example illustrates how to implement different representations of a single model.
The first representation is _outer_ (`outer_receipt_retort`),
it has a lot of validations and is used to load data from untrusted sources, e.g. API users.
The second is _inner_ (`inner_receipt_retort`) which contains less validation that speeds up loading data.
It can be used to load and dump data for internal API to communicate between services.

Also, this example shows some other advanced concepts like
adding support for custom types (`PhoneNumber` and `Money`)
and provider chaining.

Another important concept behind this example is that there are no general retort objects.
You can define a retort configured to work with a specific type
and then include this retort to another responsible for the entire API endpoints.

For simplicity, `inner_receipt_retort` and `outer_receipt_retort` are contained in one module,
but in a production code, most likely, they should be placed in their
[Interface Adapters](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html#interface-adapters)
layer
