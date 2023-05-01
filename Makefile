.PHONY: lint
lint:
	@tox -e lint


.PHONY: test-all
test-all:
	@tox -e $$(tox -l | grep '^py' | tr '\n' ',')


.PHONY: test-all-p
test-all-p:
	@tox -e $$(tox -l | grep '^py' | sort -r | tr '\n' ',') -p auto


.PHONY: test
test:
	@tox -e $$(tox -l | grep '^py' | grep 'new$$' | tr '\n' ',')


.PHONY: cov
cov:
	@coverage erase
	@tox -e $$(tox -l | grep -e '^py' | grep -v 'bench' | sort -r | tr '\n' ',') -p auto -- --cov adaptix --cov-append
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
	@for file in requirements/*.txt; do sed -i -E "s/-e file:.+\/benchmarks/-e .\/benchmarks/" "$${file}"; done


.PHONY: venv-sync
venv-sync:
	@pip-sync requirements/pre.txt requirements/dev.txt
	@pip install -e .


SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = docs
BUILDDIR      = docs-build

.PHONY: doc
doc:
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

.PHONY: doc-clean
doc-clean:
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

.PHONY: doc-open
doc-open:
	@nohup python -m webbrowser -t "file://$(CURDIR)/docs-build/html/index.html" > /dev/null
