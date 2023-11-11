# pylint: disable=invalid-name,import-error
import shlex
from pathlib import Path
from typing import Union

from invoke import Context, task


def q(value: Union[Path, str]) -> str:
    return shlex.quote(str(value))


@task
def cov(c: Context):
    inner_bash_command = q(
        'coverage run'
        ' --branch'
        ' --data-file=.tox/cov-storage/.coverage.$TOX_ENV_NAME'
        ' -m pytest'
    )
    tox_commands = f"bash -c '{q(inner_bash_command)}'"
    c.run(
        r"tox -e $(tox -l | grep -e '^py' | grep -v 'bench' | sort -r | tr '\n' ',')"
        " -p auto"
        "  --override 'testenv.allowlist_externals=bash'"
        f" --override 'testenv.commands={tox_commands}'",
        pty=True,
    )
    c.run('coverage combine --data-file .tox/cov-storage/.coverage .tox/cov-storage')
    c.run('coverage xml --data-file .tox/cov-storage/.coverage')


@task
def deps_compile(c: Context):
    promises = [
        c.run(
            f'pip-compile {req} -o {Path("requirements") / req.name}'
            ' -q --allow-unsafe --strip-extras --upgrade',
            asynchronous=True,
        )
        for req in Path('.').glob('requirements/raw/*.txt')
        if not req.name.startswith('_')
    ]
    for promise in promises:
        promise.join()

    for file in Path('.').glob('requirements/*.txt'):
        c.run(fr'sed -i -E "s/-e file:.+\/tests\/tests_helpers/-e .\/tests\/tests_helpers/" {file}')
        c.run(fr'sed -i -E "s/-e file:.+\/benchmarks/-e .\/benchmarks/" {file}')
