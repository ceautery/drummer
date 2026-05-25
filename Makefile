export PATH := venv/bin:$(PATH)

.PHONY: install lint format check test test-e2e

install:
	pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .
	pyright drummer

format:
	ruff format .
	ruff check --fix .

test:
	pytest tests/unit tests/integration -q

test-e2e:
	pytest tests/e2e -v

check: lint test
