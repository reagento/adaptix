# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = docs
BUILDDIR      = build

L_RED = \033[1;31m
NC = \033[0m

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: lint
lint:
	@tox -e lint


.PHONY: test-all
test-all:
	@tox -e $$(tox -l | grep '^py' | tr '\n' ',')


.PHONY: test
test:
	@tox -e $$(tox -l | grep '^py' | grep 'new$$' | tr '\n' ',')


.PHONY: cov
cov:
	@coverage erase
	@tox -e $$(tox -l | grep '^py' | sort -r | tr '\n' ',') -p auto -- --cov _dataclass_factory --cov-append
	@coverage xml


.PHONY: setup
setup:
	pip install -r requirements/pre.txt
	pip install -e .
	pip install -r requirements/dev.txt
	pre-commit
	pre-commit install


.PHONY: deps-compile
deps-compile:
	@for file in requirements/raw/*.txt; do pip-compile "$${file}" -o requirements/$$(basename "$$file") -q --resolver=backtracking --allow-unsafe; done
	@# pip-compile saves local packages by absolute path, fix it
	@for file in requirements/*.txt; do sed -i -E "s/-e file:.+\/tests_helpers/-e .\/tests_helpers/" "$${file}"; done


.PHONY: venv-sync
venv-sync:
	@pip-sync requirements/pre.txt requirements/dev.txt
	@pip install -e .
