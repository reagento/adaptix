Sometimes you want to split interdependent models into several files.
This results in some imports being visible only to type checkers.
Analysis of such type hints is not available at runtime.


Let's imagine that we have two files:

.. literalinclude:: /examples/common/dealing_with_type_checking/chat.py
   :caption: File ``chat.py``
   :lines: 2-

.. literalinclude:: /examples/common/dealing_with_type_checking/message.py
   :caption: File ``message.py``


If you try to get type hints at runtime, you will fail:

.. literalinclude:: /examples/common/dealing_with_type_checking/error_on_analysis.py

At runtime, these imports are not executed, so the builtin analysis function can not resolve forward refs.

Adaptix can overcome this via :func:`.type_tools.exec_type_checking`.
It extracts code fragments defined under ``if TYPE_CHECKING`` and ``if typing.TYPE_CHECKING`` constructs
and then executes them in the context of module.
As a result, the module namespace is filled with missing names, and *any* introspection function can acquire types.

You should call ``exec_type_checking`` after all required modules can be imported.
Usually, it must be at ``main`` module.

.. literalinclude:: /examples/common/dealing_with_type_checking/main.py
   :caption: File ``main.py``
   :lines: 2-
