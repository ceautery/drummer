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

Current phase: **11 — Workspaces**
