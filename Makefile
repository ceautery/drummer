VENV    := $(CURDIR)/venv
PYTHON  := $(VENV)/bin/python
RUFF    := $(VENV)/bin/ruff
PYRIGHT := $(VENV)/bin/pyright
PYTEST  := $(VENV)/bin/pytest
MKDOCS  := $(VENV)/bin/mkdocs
HATCH   := $(VENV)/bin/hatch
NPM     := npm

PROJECT ?=

.PHONY: install lint format check test test-file test-e2e dev e2e build-frontend dist docs docs-serve

install:
	pip install -e ".[dev]"
	cd frontend && $(NPM) install

lint:
	$(RUFF) check .
	$(RUFF) format --check .
	$(PYRIGHT) drummer
	cd frontend && $(NPM) run check

format:
	$(RUFF) format .
	$(RUFF) check --fix .
	cd frontend && $(NPM) run check:fix

test:
	$(PYTEST) tests/unit tests/integration -q

test-file:
	$(PYTEST) $(FILE) -v

test-e2e:
	$(PYTEST) tests/e2e -v

check: lint test

build-frontend:
	cd frontend && $(NPM) run build

dist: build-frontend
	$(HATCH) build
	$(PYTHON) scripts/dist.py

docs:
	$(MKDOCS) build

docs-serve:
	$(MKDOCS) serve

dev:
ifndef PROJECT
	$(error Usage: make dev PROJECT=/path/to/your/project)
endif
	trap 'kill 0' EXIT; (cd frontend && $(NPM) run dev) & $(PYTHON) -m drummer.cli serve --project $(PROJECT)

e2e: build-frontend test-e2e
