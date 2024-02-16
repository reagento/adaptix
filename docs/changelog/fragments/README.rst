This directory contains "news fragments" which are short files that contain a small **ReST**-formatted
text that will be added to the next ``CHANGELOG``.

The ``CHANGELOG`` will be read by **users**, so this description should be aimed to users
instead of describing internal changes which are only relevant to the developers.

Make sure to use full sentences in the **past or present tense** and use punctuation, examples::

    Improved verbose diff output with sequences.

    Terminal summary statistics now use multiple colors.

Each file should be named like ``<ISSUE>.<TYPE>.rst``, where
``<ISSUE>`` is an issue number, and ``<TYPE>`` is one of:

* ``breaking``: a change which may break existing suites, such as feature removal or behavior change.
* ``deprecation``: feature deprecation.
* ``feature``: new user facing features, like new command-line options and new behavior.
* ``bugfix``: fixes a bug.
* ``other``: any

So for example: ``123.feature.rst``, ``456.bugfix.rst``.

If your PR fixes an issue, use that number here. If there is no issue,
then after you submit the PR and get the PR number you can add a
changelog using that instead.
