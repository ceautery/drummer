# Phase 18 — Agent-ergonomic send — Design

**Date:** 2026-05-30
**Status:** Approved (brainstorming)
**Arc:** Agent API Toolkit (`docs/superpowers/specs/2026-05-30-agent-api-toolkit-arc-design.md`) — first sub-phase; sets the output conventions the later sub-phases follow.

## Context

Drummer is driven by AI agents over MCP (`FastApiMCP(app)` mirrors the REST routes as MCP
tools). The current agent-facing "send" is the **SSE** endpoint `POST /api/send`
(`EventSourceResponse`) — the wrong shape for an MCP tool, which should return a single
JSON object, not an event stream. The clean `send_request_impl` in
`drummer/api/mcp/tools.py` is **only used by tests**; `register_mcp_tools` is a no-op, so it
is not part of the live MCP surface.

This phase gives agents a proper send: one structured JSON result, with three affordances
that keep an agent's context window from flooding — **dry-run**, **field extraction**, and
**body truncation**.

## Decisions (from brainstorming)
- A **new dedicated JSON route** `POST /api/agent/send` (not the SSE route, not the parallel
  `_impl`). It reuses the same core path the SSE route uses: `parse_request_file` →
  `load_environment` → `resolve()` → `engine.send`.
- **jsonpath-ng** for the `extract` query language (standard JSONPath syntax).
- Real sends **persist to history** (parity with the SSE route; also lets Phase 21's
  snapshot/diff use agent sends). Dry-runs do not persist.
- `sent` returns **real header values** (no masking) — masking was a UI display concern; an
  agent needs the actual values it sent.

## Architecture

Additive within existing layers (`core` ← `api`). No layer-boundary change, no ADR. No
frontend changes. The SSE `/api/send` route and the UI are untouched.

### New dependency
- `jsonpath-ng` added to `pyproject.toml` dependencies.

### Pure core helpers (web-free, independently testable)
`drummer/core/agent_shaping.py` (new):
- `extract_jsonpath(body_text: str, expr: str) -> tuple[list[object] | None, str | None]`
  - Parses `body_text` as JSON, compiles `expr` with jsonpath-ng, returns
    `(matches, None)` where `matches` is the list of matched values (empty list if the path
    matches nothing). On invalid JSON or an invalid expression, returns `(None, error)` with
    a short human-readable message.
- `truncate_body(body: str, max_chars: int | None) -> tuple[str, bool, int]`
  - Returns `(text, truncated, total_chars)`. `max_chars=None` → no truncation
    (`truncated=False`). Otherwise truncate to `max_chars`, `truncated=True` when the body
    was longer.

### New route
`drummer/api/routes/agent.py` (new) → `POST /api/agent/send`, mounted under `/api` in
`create_app`. Given an explicit `operation_id="agent_send"` so the mirrored MCP tool has a
clear name. Reuses the same dependencies as the SSE route (`project_dir`, `cookie_jar`,
`oauth_cache`, `db_factory`, `transport`, `active_environment`).

**Request body `AgentSendBody`:**
- `path: str`
- `environment: str = ""` (empty → app's active environment)
- `overrides: dict[str, str] = {}`
- `dry_run: bool = False`
- `extract: str | None = None` (JSONPath expression)
- `max_body_chars: int | None = 2048` (truncation threshold; `null` → full body)

**Response `AgentSendResult`:**
- `dry_run: bool`
- `status_code: int | None` (None on dry-run)
- `url: str` (the resolved request URL on dry-run; the response URL on a real send)
- `headers: list[tuple[str, str]]` (response headers; empty on dry-run)
- `elapsed_ms: float | None` (None on dry-run)
- `encoding: str | None`
- `sent: SentRequest | None` (reuses the Phase 17 engine model: method/url/params/headers/body — real values)
- `warnings: list[str]`
- `variables: dict[str, str]`
- `body: str | None`, `body_truncated: bool`, `body_total_chars: int`
- `extracted: list[object] | None`, `extract_error: str | None`

### Behavior

**Resolve (always):** parse the request file, load the environment, merge `overrides`,
`resolve()` → a `ResolvedRequest` (final URL, substituted params/headers, computed
Bearer/Basic/API-key Authorization). Project script-timeout handling matches the SSE route.

**dry_run = true:** do NOT send — no HTTP request, no OAuth token fetch, no history write.
Build `sent` from the **resolved** request (a `SentRequest` with the resolved
method/url/params/headers/body). Return `status_code=None`, `headers=[]`, `body=None`,
`body_truncated=False`, `body_total_chars=0`, `extracted=None`, plus `warnings` and
`variables`. `url` is the resolved request URL.
- **Documented caveat:** dry-run reflects variable substitution only, **not** pre-request
  script mutations (the pre-script is not executed in dry-run, to keep it side-effect-free).
  Pre-script mutations are visible only via a real send's `sent` (the Phase 17 path).

**dry_run = false (real send):** call `engine.send` (same as the SSE route). Then:
- `sent` = `result.sent` (the truly-sent request from Phase 17); `warnings` =
  `result.warnings`; `variables` = `result.variables`.
- **Body shaping:**
  - If `extract` is set: run `extract_jsonpath(result.body, extract)`.
    - matches (incl. empty list) → `extracted = matches`, `extract_error = None`, and
      **omit the body** (`body = None`) for context economy. `body_total_chars` still
      reports the full length.
    - error (non-JSON body or bad expression) → `extracted = None`,
      `extract_error = <message>`, and return the (truncated) `body` so the agent can debug.
  - If `extract` is not set: `body, body_truncated, body_total_chars =
    truncate_body(result.body, max_body_chars)`; `extracted = None`.
- **History:** persist a record exactly as the SSE route does today (same fields/columns).
  Do this only on a real send.
- The early script-error case (engine returns `status_code == 0` with a `script_error`):
  return the result with `status_code=0` and whatever `sent` the engine provided (may be
  `None`); no history write, consistent with the SSE route's early-exit.

### MCP exposure
The new route is a standard FastAPI route, so `FastApiMCP(app)` mirrors it as an MCP tool
automatically. No change to `register_mcp_tools` (still a no-op). The explicit
`operation_id` keeps the tool name stable/clear.

## Error handling
- Invalid request path / missing file / bad YAML → same error mapping the SSE route uses,
  surfaced as an HTTP error (the MCP layer reports it to the agent).
- `extract` against a non-JSON body or an invalid JSONPath expression → `200` with
  `extract_error` populated and the body returned (not an HTTP error — the send succeeded).
- Network/transport errors during a real send → propagate as the SSE route does.

## Testing
- **Core unit (`tests/unit/test_agent_shaping.py`):**
  - `extract_jsonpath`: a matching path returns the value(s); a non-matching path returns
    `([], None)`; a non-JSON body returns `(None, error)`; an invalid expression returns
    `(None, error)`.
  - `truncate_body`: under threshold (no truncation), over threshold (truncated + flags),
    `None` (full body).
- **Integration (`tests/integration/test_agent_route.py`, using `client_with_mock`):**
  - Real send → `AgentSendResult` with `status_code`, `sent` (method/url), `warnings`.
  - `dry_run` → `sent` reflects substitution, `status_code is None`, and **no** history row
    was written (assert history count unchanged).
  - `extract` with a matching path → `extracted` populated and `body is None`.
  - `extract` with a non-JSON body → `extract_error` set and `body` present.
  - Oversized body + small `max_body_chars` → `body_truncated is True`,
    `body_total_chars` == full length.
  - A request whose URL has an unresolved `{{var}}` → non-empty `warnings`.

## Out of scope (YAGNI / later phases)
- Assertions and suite runs (Phases 19–20), snapshot/diff (Phase 21).
- Changes to the SSE `/api/send` route or any frontend.
- Wiring or removing the now-unused `_impl` functions in `tools.py` (note the disconnect;
  a cleanup could retire them in a later phase, but it's out of scope here).
