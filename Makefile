# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = docs
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile lint test-all test cov setup

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

lint:
	@tox -e lint

test-all:
	@tox -e $$(tox -l | grep '^py' | tr '\n' ',')

test:
	@tox -e $$(tox -l | grep '^py' | grep 'new$$' | tr '\n' ',')

cov:
	@coverage erase
	@tox -e $$(tox -l | grep '^py' | sort -r | tr '\n' ',') -p auto -- --cov dataclass_factory_30 --cov-append
	@coverage xml

setup:
	pip install -e .
	pip install -r requirements.txt
	pre-commit install
