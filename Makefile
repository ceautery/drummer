VENV    := $(CURDIR)/venv
PYTHON  := $(VENV)/bin/python
RUFF    := $(VENV)/bin/ruff
PYRIGHT := $(VENV)/bin/pyright
PYTEST  := $(VENV)/bin/pytest

.PHONY: install lint format check test test-file test-e2e

install:
	pip install -e ".[dev]"

lint:
	$(RUFF) check .
	$(RUFF) format --check .
	$(PYRIGHT) drummer

format:
	$(RUFF) format .
	$(RUFF) check --fix .

test:
	$(PYTEST) tests/unit tests/integration -q

test-file:
	$(PYTEST) $(FILE) -v

test-e2e:
	$(PYTEST) tests/e2e -v

check: lint test
