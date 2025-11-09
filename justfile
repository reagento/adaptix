set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

just := "just --justfile " + justfile()
uv_sync_group := "uv sync --active --locked --only-group"

[private]
@install-initial:
    pip install pip==25.1.1
    pip install uv==0.9.8


[private]
@default:
    {{ just }} --list

# prepare venv and repo for developing
@bootstrap:
    {{ just }} install-initial
    {{ just }} venv-sync
    prek
    prek install

# sync version of installed packages
@venv-sync:
    {{ uv_sync_group }} dev

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
    uv lock

@deps-compile-upgrade:
    uv lock --upgrade

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
@setup-ci-runner:
    {{ just }} install-initial
    {{ uv_sync_group }} runner
    echo ".venv/bin" >> "$GITHUB_PATH"

[private]
@inv *ARGS:
    {{ inv }} {{ ARGS }}
