from setuptools import setup

# can not use pyproject.toml because it requires to access to module as tests_helpers.tests_helpers

setup(
    name='tests_helpers',
    version='0.0.0',
    py_modules=['tests_helpers'],
)
