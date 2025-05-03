Remove ``hide_traceback`` parameter of ``Retort`` (it is also removed from ``Retort.replace`` method).
Now, you can control rendering error via ``error_renderer``. Yo can pass ``None`` to show python ``ExceptionGroup``
