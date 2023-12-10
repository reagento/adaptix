[private]
@default:
    just --list

@bootstrap:
    pip install -r requirements/pre.txt
    pip install -e .
    pip install -r requirements/dev.txt
    pre-commit
    pre-commit install

@venv-sync:
    pip-sync requirements/pre.txt requirements/dev.txt
    pip install -e .

@setup-runner:
    pip install -r requirements/pre.txt
    pip install -r requirements/runner.txt

@lint:
    tox -e lint

@test:
    tox -e $(tox list --no-desc | grep '^py' | grep 'new$' | tr '\n' ',')

@test-all:
    tox -e $(tox list --no-desc | grep '^py' | sort -r | tr '\n' ',')

@test-all-p:
    tox -e $(tox list --no-desc | grep '^py' | sort -r | tr '\n' ',') -p auto

@test-on-python-version target:
    tox -e $(tox list --no-desc | grep '^{{ target }}' | sort -r | tr '\n' ',')

@cov:
    inv cov

@deps-compile:
    inv deps-compile

doc_source := "docs"
doc_target := "docs-build"

@doc:
    sphinx-build -M html {{ doc_source }} {{ doc_target }}
    echo "Open file://`pwd`/{{ doc_target }}/html/index.html"

@doc-clean:
    sphinx-build -M clean {{ doc_source }} {{ doc_target }}

@doc-open:
    nohup python -m webbrowser -t "file://`pwd`/docs-build/html/index.html" > /dev/null
