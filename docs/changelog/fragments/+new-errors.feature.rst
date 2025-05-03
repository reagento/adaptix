Completely rework error rendering.
Now, all errors of loader, dumper and converter generation uses new, compact and clear display mode.
Also, many error texts are improved.

.. code-block:: text
   :caption: Old error example

      | adaptix.AggregateCannotProvide: Cannot create loader for model. Loaders for some fields cannot be created (1 sub-exception)
      | Location: `Book`
      +-+---------------- 1 ----------------
        | adaptix.AggregateCannotProvide: Cannot create loader for model. Cannot fetch InputNameLayout (1 sub-exception)
        | Location: `Book.author: Person`
        +-+---------------- 1 ----------------
          | adaptix.CannotProvide: Required fields ['last_name'] are skipped
          | Location: `Book.author: Person`
          +------------------------------------

    The above exception was the direct cause of the following exception:

    Traceback (most recent call last):
      ...
    adaptix.ProviderNotFoundError: Cannot produce loader for type <class '__main__.Book'>
    Note: The attached exception above contains verbose description of the problem



.. code-block:: text
   :caption: New error example

    Traceback (most recent call last):
      ...
    adaptix.ProviderNotFoundError: Cannot produce loader for type <class '__main__.Book'>
      × Cannot create loader for model. Loaders for some fields cannot be created
      │ Location: ‹Book›
      ╰──▷ Cannot create loader for model. Cannot fetch `InputNameLayout`
         │ Location: ‹Book.author: Person›
         ╰──▷ Required fields ['last_name'] are skipped
