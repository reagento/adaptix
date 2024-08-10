set windows-powershell := true

[private]
@default:
    just --list

# prepare venv and repo for developing
@bootstrap:
    pip install -r requirements/pre.txt
    uv pip install -e .
    uv pip install -r requirements/dev.txt
    pre-commit
    pre-commit install

# sync version of installed packages
@venv-sync:
    uv pip sync requirements/pre.txt requirements/dev.txt
    uv pip install -e .

# run all linters
@lint:
    tox -e lint

# run basic tests on all python versions
@test:
    tox -e $(tox list --no-desc | grep '^py' | grep 'new$' | tr '\n' ',')

# run all tests on all python versions
@test-all-seq:
    tox -e $(tox list --no-desc | grep '^py' | sort -r | tr '\n' ',')

# run all tests on all python versions parallelly
@test-all:
    tox -e $(tox list --no-desc | grep '^py' | sort -r | tr '\n' ',') -p auto

inv := "inv -r scripts -c invoke_tasks"

@cov output='coverage.xml':
    {{ inv }} cov \
      --env-list $(tox list --no-desc | grep -e '^py' | grep -v '^pypy' | sort -r | tr '\n' ',') \
      --output {{ output }} \
      --parallel

@deps-compile:
    {{ inv }} deps-compile

@deps-compile-upgrade:
    {{ inv }} deps-compile --upgrade

doc_source := "docs"
doc_target := "docs-build"

# build documentation
@doc:
    sphinx-build -M html {{ doc_source }} {{ doc_target }}
    echo "Open file://`pwd`/{{ doc_target }}/html/index.html"

# clean generated documentation and build cache
@doc-clean:
    sphinx-build -M clean {{ doc_source }} {{ doc_target }}


@changelog version='Preview':
    towncrier build --keep --version {{ version }}

# Continious integration

[private]
@setup-runner:
    pip install -r requirements/pre.txt
    uv pip install -r requirements/runner.txt

[private]
@inv *ARGS:
    {{ inv }} {{ ARGS }}
