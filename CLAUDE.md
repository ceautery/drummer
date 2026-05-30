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

The original 14-phase build arc is complete. Work since then proceeds in follow-on arcs,
each phase with its own spec + plan in `docs/superpowers/`. Don't implement a later phase
while working an earlier one.

**See `ROADMAP.md` and `TODO.md` for live status.** As of this writing: the post-1.0
hardening arc (F1, F2, Phases 15–17) is complete, and the Agent API Toolkit arc is in
progress — Phase 18 (agent-ergonomic send) done; **next is Phase 19 (assertions & captures)**.
