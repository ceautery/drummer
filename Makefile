VENV    := $(CURDIR)/venv
PYTHON  := $(VENV)/bin/python
RUFF    := $(VENV)/bin/ruff
PYRIGHT := $(VENV)/bin/pyright
PYTEST  := $(VENV)/bin/pytest
NPM     := npm

PROJECT ?=

.PHONY: install lint format check test test-file test-e2e dev e2e build-frontend

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

dev:
ifndef PROJECT
	$(error Usage: make dev PROJECT=/path/to/your/project)
endif
	trap 'kill 0' EXIT; (cd frontend && $(NPM) run dev) & $(PYTHON) -m drummer.cli serve --project $(PROJECT)

e2e: build-frontend test-e2e
