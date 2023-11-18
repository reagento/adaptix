from setuptools import setup

# cannot use pyproject.toml because it requires accessing to module as tests_helpers.tests_helpers

setup(
    name='tests_helpers',
    version='0.0.0',
    py_modules=['tests_helpers'],
)
