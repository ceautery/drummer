# Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the full Drummer project structure with working linting, type checking, a CLI stub, a test harness, CI, and two ADRs — everything needed so Phase 2 can start writing real code against a clean, green baseline.

**Architecture:** Layered monorepo — `drummer/` (Python package) / `frontend/` (React, Phase 5) / `tests/` / `docs/`. Phase 1 establishes the Python side only; Biome/frontend tooling is stubbed for Phase 5. All commits must pass the pre-commit hook before landing.

**Tech Stack:** Python 3.12, FastAPI, Typer, Ruff (strict), Pyright (strict), Pytest, GitHub Actions

---

## File Map

Files created in this phase:

```
drummer/
├── drummer/
│   ├── __init__.py           version string
│   ├── cli.py                Typer app, all top-level commands stubbed
│   ├── core/__init__.py      empty package marker
│   ├── api/__init__.py       empty package marker
│   └── mock/__init__.py      empty package marker
├── tests/
│   ├── conftest.py           asyncio_mode config, shared fixtures placeholder
│   ├── unit/
│   │   ├── __init__.py
│   │   └── test_cli.py       CLI smoke tests
│   ├── integration/
│   │   └── __init__.py
│   └── e2e/
│       └── __init__.py
├── docs/
│   └── decisions/
│       ├── 001-quickjs-scripting.md
│       └── 002-yaml-frontmatter-format.md
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── biome.json                frontend stub (no files to lint yet)
├── Makefile
├── pyrightconfig.json
├── pyproject.toml            all deps + ruff/pyright/pytest config
├── CLAUDE.md
├── TODO.md
├── ROADMAP.md
└── scripts/
    └── pre-commit            git hook script
```

---

## Task 1: Directory scaffold and .gitignore

**Files:**
- Create: `.gitignore`
- Create: `drummer/__init__.py`
- Create: `drummer/core/__init__.py`
- Create: `drummer/api/__init__.py`
- Create: `drummer/mock/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/e2e/__init__.py`
- Create: `scripts/` directory

- [ ] **Step 1: Create directory tree**

```bash
mkdir -p drummer/core drummer/api drummer/mock
mkdir -p tests/unit tests/integration tests/e2e
mkdir -p docs/decisions .github/workflows scripts
```

- [ ] **Step 2: Write .gitignore**

Create `.gitignore`:

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
.env

# Frontend (Phase 5)
node_modules/
frontend/dist/
drummer/api/static/

# Brainstorm artifacts
.superpowers/

# macOS
.DS_Store

# Editor
.idea/
.vscode/

# Test artifacts
.pytest_cache/
htmlcov/
.coverage
playwright-report/
test-results/
```

- [ ] **Step 3: Write package markers**

Create `drummer/__init__.py`:
```python
__version__ = "0.1.0"
```

Create `drummer/core/__init__.py`, `drummer/api/__init__.py`, `drummer/mock/__init__.py` — all empty files:
```bash
touch drummer/core/__init__.py drummer/api/__init__.py drummer/mock/__init__.py
```

- [ ] **Step 4: Write tests/conftest.py**

```python
import pytest
```

- [ ] **Step 5: Write test package markers**

```bash
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py tests/e2e/__init__.py
```

- [ ] **Step 6: Commit**

```bash
git add .gitignore drummer/ tests/ docs/ scripts/ .github/
git commit -m "chore: initial directory scaffold"
```

---

## Task 2: pyproject.toml

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Write pyproject.toml**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "drummer"
version = "0.1.0"
description = "A local, standalone REST client — free alternative to Postman/Insomnia/Bruno"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "httpx>=0.27",
    "python-quickjs>=1.0",
    "python-frontmatter>=1.1",
    "pydantic>=2.7",
    "aiosqlite>=0.20",
    "sqlalchemy>=2.0",
    "fastapi-mcp>=0.3",
    "chardet>=5.2",
    "typer>=0.12",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.5",
    "pyright>=1.1",
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "pytest-playwright>=0.5",
]

[project.scripts]
drummer = "drummer.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["drummer"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["ALL"]
ignore = [
    "D",      # docstrings — concise code over coverage
    "ANN101", # missing type annotation for self
    "ANN102", # missing type annotation for cls
    "COM812", # trailing comma — conflicts with formatter
    "ISC001", # implicit string concat — conflicts with formatter
    "ERA001", # commented-out code — too aggressive
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "ANN"]   # assert + missing annotations fine in tests
```

- [ ] **Step 2: Install in development mode**

```bash
pip install -e ".[dev]"
```

Expected: all packages install without errors.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add pyproject.toml with all dependencies"
```

---

## Task 3: Ruff and Pyright configuration

**Files:**
- Modify: `pyproject.toml` (Ruff config already in Task 2)
- Create: `pyrightconfig.json`

- [ ] **Step 1: Write pyrightconfig.json**

Create `pyrightconfig.json`:

```json
{
  "pythonVersion": "3.12",
  "typeCheckingMode": "strict",
  "include": ["drummer"],
  "exclude": ["tests", "frontend", ".venv", "venv"]
}
```

- [ ] **Step 2: Verify Ruff passes on current files**

```bash
ruff check .
```

Expected: no errors. If errors appear, fix them before continuing — do not add `# noqa` comments.

- [ ] **Step 3: Verify Ruff format**

```bash
ruff format --check .
```

Expected: no reformatting needed. If changes are needed, run `ruff format .` and inspect each change.

- [ ] **Step 4: Verify Pyright passes on current files**

```bash
pyright drummer
```

Expected: 0 errors, 0 warnings. Fix any type errors at the source.

- [ ] **Step 5: Commit**

```bash
git add pyrightconfig.json pyproject.toml
git commit -m "chore: configure Ruff (strict) and Pyright (strict)"
```

---

## Task 4: CLI stub

**Files:**
- Create: `drummer/cli.py`
- Create: `tests/unit/test_cli.py`

- [ ] **Step 1: Write the failing tests first**

Create `tests/unit/test_cli.py`:

```python
from typer.testing import CliRunner

from drummer.cli import app

runner = CliRunner()


def test_help_shows_drummer():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Drummer" in result.output


def test_serve_command_exists():
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output


def test_new_command_exists():
    result = runner.invoke(app, ["new", "--help"])
    assert result.exit_code == 0


def test_export_command_exists():
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0


def test_mcp_command_exists():
    result = runner.invoke(app, ["mcp", "--help"])
    assert result.exit_code == 0


def test_attribution_option_exists():
    result = runner.invoke(app, ["--attribution"])
    assert result.exit_code == 0
    assert "Metropolitan Museum" in result.output
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/unit/test_cli.py -v
```

Expected: all tests FAIL with `ImportError: cannot import name 'app' from 'drummer.cli'`

- [ ] **Step 3: Implement drummer/cli.py**

Create `drummer/cli.py`:

```python
import typer

from drummer import __version__

_ATTRIBUTION = (
    "Drummer includes data from the Metropolitan Museum of Art Open Access collection.\n"
    "License: Creative Commons Zero (CC0)\n"
    "Source: https://www.metmuseum.org/about-the-met/policies-and-documents/open-access\n"
    "The Met makes its Open Access data available for unrestricted use."
)

app = typer.Typer(
    name="drummer",
    help="Drummer — a local REST client.",
    no_args_is_help=True,
)


@app.callback()
def main(
    attribution: bool = typer.Option(False, "--attribution", help="Print dataset credits and exit."),
    version: bool = typer.Option(False, "--version", "-V", help="Print version and exit."),
) -> None:
    if attribution:
        typer.echo(_ATTRIBUTION)
        raise typer.Exit
    if version:
        typer.echo(f"Drummer {__version__}")
        raise typer.Exit


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on."),
) -> None:
    """Start the Drummer server and open the browser."""
    typer.echo(f"Starting Drummer on http://localhost:{port} ...")
    typer.echo("(Server not yet implemented — Phase 4)")


@app.command()
def new(path: str = typer.Argument(..., help="Path for the new project folder.")) -> None:
    """Create a new Drummer project at PATH."""
    typer.echo(f"Creating project at {path} ...")
    typer.echo("(Not yet implemented — Phase 2)")


@app.command()
def export(path: str = typer.Argument(..., help="Path of the project to export.")) -> None:
    """Export a Drummer project at PATH as a zip file."""
    typer.echo(f"Exporting project at {path} ...")
    typer.echo("(Not yet implemented — Phase 2)")


@app.command()
def mcp() -> None:
    """Print MCP server connection info."""
    typer.echo("MCP server info: not yet implemented — Phase 4")
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/unit/test_cli.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run Ruff and Pyright on new file**

```bash
ruff check drummer/cli.py && pyright drummer/cli.py
```

Expected: no errors. Fix any issues at the root.

- [ ] **Step 6: Commit**

```bash
git add drummer/cli.py tests/unit/test_cli.py
git commit -m "feat: add CLI stub with all top-level commands"
```

---

## Task 5: Makefile and pre-commit hook

**Files:**
- Create: `Makefile`
- Create: `scripts/pre-commit`

- [ ] **Step 1: Write Makefile**

Create `Makefile`:

```makefile
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
```

- [ ] **Step 2: Verify make check passes**

```bash
make check
```

Expected: lint passes, 6 tests pass, no failures.

- [ ] **Step 3: Write pre-commit hook script**

Create `scripts/pre-commit`:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "▶ Running pre-commit checks (make check)..."
make check
echo "✓ All checks passed."
```

- [ ] **Step 4: Make the script executable**

```bash
chmod +x scripts/pre-commit
```

- [ ] **Step 5: Install the hook**

```bash
cp scripts/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

- [ ] **Step 6: Verify the hook runs**

```bash
.git/hooks/pre-commit
```

Expected: "✓ All checks passed."

- [ ] **Step 7: Commit**

```bash
git add Makefile scripts/pre-commit
git commit -m "chore: add Makefile and pre-commit hook"
```

---

## Task 6: Biome configuration (frontend stub)

**Files:**
- Create: `biome.json`

- [ ] **Step 1: Write biome.json**

Create `biome.json` at the repo root (Biome will be run over `frontend/src` in Phase 5; creating the config now establishes the standard):

```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.0/schema.json",
  "organizeImports": {
    "enabled": true
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true
    }
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "files": {
    "include": ["frontend/src/**"]
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add biome.json
git commit -m "chore: add Biome config for frontend (Phase 5)"
```

---

## Task 7: CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Write CLAUDE.md**

Create `CLAUDE.md`:

```markdown
# Drummer — Claude Directives

## Development approach

Default to **subagent-driven development** (superpowers:subagent-driven-development skill) for any
non-trivial task. Trivial = single file, no new dependencies, obvious implementation.

## Before every commit

All of these must pass — no exceptions:

```bash
make check   # ruff + pyright + pytest tests/unit tests/integration
```

Fix linting and type errors at the root. Never use `# noqa`, `# type: ignore`,
`// eslint-disable`, or any other suppression comment. Doing things right is always in scope.

## Code standards

- No suppression comments — fix the root cause
- No untyped dicts in API responses — use Pydantic models
- No business logic in FastAPI route handlers — call `drummer/core`
- No direct file I/O outside `drummer/core/storage/`
- ADR required before changing any layer boundary (core ↔ api ↔ frontend ↔ mcp)

## Project management

- `TODO.md` — current sprint only, nothing backlogged
- `ROADMAP.md` — high-level milestone view
- `docs/decisions/` — Architecture Decision Records
- `docs/superpowers/specs/` — design specs from brainstorming
- `docs/superpowers/plans/` — implementation plans

## Layer boundaries

```
drummer/core/     ← pure Python, no web framework, independently testable
drummer/api/      ← FastAPI; calls core; no business logic in handlers
drummer/api/mcp/  ← thin MCP adapters over core
frontend/         ← React + Vite; compiled to drummer/api/static/
```

## Build phases

This project is built in 10 phases, each with its own plan in `docs/superpowers/plans/`.
Do not implement features from a later phase while working in an earlier one.

Current phase: **1 — Foundation**
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "chore: add CLAUDE.md with development directives"
```

---

## Task 8: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write ci.yml**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    name: Lint + Unit + Integration
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Ruff lint
        run: ruff check .

      - name: Ruff format check
        run: ruff format --check .

      - name: Pyright type check
        run: pyright drummer

      - name: Unit + Integration tests
        run: pytest tests/unit tests/integration -v

  e2e:
    name: E2E (Playwright)
    runs-on: ubuntu-latest
    needs: check
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install Python dependencies
        run: pip install -e ".[dev]"

      - name: Install Playwright browsers
        run: playwright install --with-deps chromium

      - name: E2E tests
        run: pytest tests/e2e -v
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "chore: add GitHub Actions CI workflow"
```

---

## Task 9: Architecture Decision Records

**Files:**
- Create: `docs/decisions/001-quickjs-scripting.md`
- Create: `docs/decisions/002-yaml-frontmatter-format.md`

- [ ] **Step 1: Write ADR #001**

Create `docs/decisions/001-quickjs-scripting.md`:

```markdown
# ADR 001: QuickJS for scripting engine

**Date:** 2026-05-25
**Status:** Accepted

## Context

Drummer needs a scripting engine for pre- and post-request scripts. Users need to inspect and
mutate request/response data, extract values into environment variables, and log output for
debugging. The scripting language must be familiar to API developers, safely sandboxable, and
embeddable in a Python process.

Candidates evaluated:
- **Lua** (`lupa`): battle-tested, small runtime, but unfamiliar to most API developers
- **Python subprocess**: familiar, but sandboxing safely is genuinely hard and per-script startup
  latency is noticeable
- **JavaScript via QuickJS** (`python-quickjs`): JS is the Postman mental model, the runtime is
  tiny (~210kB), sandboxing is solid, and startup is fast

## Decision

Use **QuickJS via `python-quickjs`**. Scripts run in an isolated QuickJS context per request.
The `dm` object is the only API surface exposed to scripts.

## Consequences

- Users write pre/post scripts in JavaScript — consistent with Postman muscle memory
- The sandbox boundary is well-defined: scripts cannot import modules or access the filesystem
- `python-quickjs` must be available as a binary wheel for the target platforms (macOS, Linux)
- New `dm.*` API methods require changes to the QuickJS context setup in `drummer/core/scripting.py`
```

- [ ] **Step 2: Write ADR #002**

Create `docs/decisions/002-yaml-frontmatter-format.md`:

```markdown
# ADR 002: YAML frontmatter + Markdown body for request files

**Date:** 2026-05-25
**Status:** Accepted

## Context

Request definitions need to be stored in a human-readable, git-diffable format. HTTP requests
have structured metadata (method, URL, headers, auth, scripts, params) alongside free-form
documentation. Three formats were evaluated:

- **JSON**: machine-friendly, terrible for humans to read or diff
- **Pure YAML**: clean, simple to parse, good tooling, no documentation story
- **YAML frontmatter + Markdown body**: structured metadata in the YAML block, free-form
  documentation, notes, and example responses in the Markdown body

## Decision

Use **YAML frontmatter + Markdown body**. One `.md` file per request. The YAML block holds all
structured request metadata; the Markdown body is documentation for that request.

Parsed using `python-frontmatter`. Schema validated using Pydantic v2.

## Consequences

- Request files are readable and writable by hand without tooling
- Git diffs are meaningful: changing a header shows up as a one-line diff
- The Markdown body doubles as living documentation for each request
- We maintain a custom schema (validated by Pydantic) — adding new fields requires updating
  `drummer/core/storage/formats.py` and the Pydantic model
- Tooling that expects pure YAML or pure JSON will not work with request files without a converter
```

- [ ] **Step 3: Commit**

```bash
git add docs/decisions/
git commit -m "docs: add ADR 001 (QuickJS) and ADR 002 (YAML frontmatter)"
```

---

## Task 10: TODO.md and ROADMAP.md

**Files:**
- Create: `TODO.md`
- Create: `ROADMAP.md`

- [ ] **Step 1: Write TODO.md**

Create `TODO.md`:

```markdown
# TODO

Current sprint: **Phase 2 — Storage layer**

- [ ] Implement `drummer/core/storage/formats.py` — parse/write YAML frontmatter request files
- [ ] Implement `drummer/core/storage/project.py` — load/save project metadata and environments
- [ ] Write unit tests for all storage functions
```

- [ ] **Step 2: Write ROADMAP.md**

Create `ROADMAP.md`:

```markdown
# Drummer Roadmap

| Phase | Description | Status |
|---|---|---|
| 1 — Foundation | Repo scaffold, tooling, CI, ADRs | ✅ Done |
| 2 — Storage | YAML frontmatter parser, project/environment loading | ⬜ Next |
| 3 — HTTP engine | Request send, variable substitution, cookie jar, encoding | ⬜ |
| 4 — API + MCP | FastAPI app, REST routes, MCP tools, response history | ⬜ |
| 5 — React UI | Vite scaffold, workspace view, request editor, response viewer | ⬜ |
| 6 — Scripting | QuickJS runner, dm API, script debugger | ⬜ |
| 7 — Mock server + tutorial | Met dataset, mock routes, TutorialView | ⬜ |
| 8 — GraphQL | GraphQL query building, introspection, BodyTab mode | ⬜ |
| 9 — OAuth + cookies | OAuth flow handler, persistent cookie store | ⬜ |
| 10 — Distribution | Homebrew formula, make dist, docs site | ⬜ |
```

- [ ] **Step 3: Commit**

```bash
git add TODO.md ROADMAP.md
git commit -m "docs: add TODO and ROADMAP for phase tracking"
```

---

## Task 11: Final verification

- [ ] **Step 1: Run full check suite**

```bash
make check
```

Expected output (approximately):
```
ruff check .
ruff format --check .
pyright drummer
  0 errors, 0 warnings, 0 informations
pytest tests/unit tests/integration -q
......
6 passed in 0.XXs
```

- [ ] **Step 2: Test that the CLI entry point works**

```bash
pip install -e .
drummer --help
```

Expected: help text showing "Drummer — a local REST client." with `serve`, `new`, `export`, `mcp` subcommands.

```bash
drummer --attribution
```

Expected: Met Museum attribution text.

- [ ] **Step 3: Verify git log is clean**

```bash
git log --oneline
```

Expected: 10 commits, each passing the pre-commit hook:
```
<hash> docs: add TODO and ROADMAP for phase tracking
<hash> docs: add ADR 001 (QuickJS) and ADR 002 (YAML frontmatter)
<hash> chore: add GitHub Actions CI workflow
<hash> chore: add CLAUDE.md with development directives
<hash> chore: add Biome config for frontend (Phase 5)
<hash> chore: add Makefile and pre-commit hook
<hash> feat: add CLI stub with all top-level commands
<hash> chore: configure Ruff (strict) and Pyright (strict)
<hash> chore: add pyproject.toml with all dependencies
<hash> chore: initial directory scaffold
```

- [ ] **Step 4: Update CLAUDE.md current phase**

Edit `CLAUDE.md` — change the current phase line to:
```markdown
Current phase: **2 — Storage**
```

- [ ] **Step 5: Final commit**

```bash
git add CLAUDE.md
git commit -m "chore: phase 1 complete — advance to phase 2"
```

---

## Spec Coverage Check

| Spec requirement | Covered by |
|---|---|
| Repo backed by git | Task 1 (git already initialized) |
| Ruff linting (strict) | Task 2 (pyproject.toml), Task 3 |
| Pyright type checking (strict) | Task 3 |
| Biome linting (JS) | Task 6 |
| 100% green before committing | Task 5 (pre-commit hook + Makefile) |
| CLAUDE.md — subagent-driven development directive | Task 7 |
| CLAUDE.md — no suppression comments | Task 7 |
| CLAUDE.md — ADR required for layer changes | Task 7 |
| GitHub Actions CI | Task 8 |
| ADR #001 QuickJS | Task 9 |
| ADR #002 YAML frontmatter | Task 9 |
| TODO.md + ROADMAP.md | Task 10 |
| `drummer` CLI entry point | Task 4 |
| `drummer --attribution` | Task 4 |
| Pytest test scaffold | Task 4 |
| Keep work interruptable | Frequent commits throughout |
