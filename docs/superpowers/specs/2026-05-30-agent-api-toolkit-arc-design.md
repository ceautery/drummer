# Agent API Toolkit Arc — Design

**Date:** 2026-05-30
**Status:** Approved (brainstorming) — arc-level decomposition. Each sub-phase below gets its
own spec → plan → implementation cycle in a later session.

## Motivation

Drummer is a REST client built for humans, but it is also driven by AI agents over MCP
(`drummer/api/mcp/tools.py` mirrors the REST routes as MCP tools via `fastapi-mcp`). This
arc makes Drummer a genuinely better tool than `curl` for an agent doing **API refactoring
and testing** — the loop where an agent repeatedly sends a request, checks the result,
compares it against a baseline, and chains calls together.

### What already beats curl (build on, don't redesign)
- **Named persistent requests** (markdown + frontmatter) — no re-pasting long commands.
- **Environments + variables, OAuth client-credentials, persistent cookies** — no manual
  token juggling; secrets live outside the request.
- **Pre/post JS scripts**, **response history**, and (Phase 17) **visibility into the exact
  request sent**.
- An **MCP surface** already exposing list/get/create/update/send requests, history, and
  environment/cookie management.

### The gaps this arc closes (agent-specific wins over curl)
1. No first-class **assertions** → agents reinvent `curl | jq | bash` checks each time.
2. No **contract diffing** across runs → "did my refactor change the API?" means saving
   two files and eyeballing.
3. Raw response bodies **flood an agent's context window** → no field extraction,
   truncation, or diff-only output.
4. No declarative **value extraction / chaining** → multi-step flows (login → CRUD →
   cleanup) require hand-written post-scripts.

## Cross-cutting design principles

- **Context economy first.** Every MCP tool added in this arc returns compact, structured
  output by default (status + timing + only what was asked for), never a raw body dump.
  Large bodies are truncated/summarized with an explicit opt-in to retrieve more.
- **Declarative over scripted.** Assertions, captures, and chaining are declared in the
  request frontmatter / suite config and evaluated by the engine — not hand-written JS —
  so an agent can read and write them structurally. (Post-scripts remain for escape-hatch
  logic.)
- **Layer boundaries preserved.** Response-evaluation logic lives in `drummer/core`; the
  API/MCP layers are thin adapters. No business logic in route handlers. File I/O stays in
  `drummer/core/storage/`. An ADR is required only if a sub-phase changes a layer boundary.
- **TDD + green commits.** Each sub-phase follows the project's existing discipline
  (`make check`; run `npm run test` for frontend changes since `make check` skips vitest).

## Sub-phases

Dependency chain: **18 → 19 → 20**; **21** depends only on 18's output conventions and can
be built any time after 18. Recommended start: **Phase 18** (smallest, sets the output
contract, reuses Phase 17).

### Phase 18 — Agent-ergonomic send (conventions layer)
**Goal:** Make the MCP/send path usable in a tight agent loop without flooding context.
**Scope:**
- **Dry-run:** return the resolved/truly-sent request (reusing Phase 17's `SentRequest`)
  **without** sending — lets an agent confirm substitution/auth before firing.
- **Field extraction:** a JSONPath `extract` parameter on send → response carries only the
  matched value(s) instead of the full body.
- **Body shaping:** truncation/summarization of large bodies, with size metadata and an
  explicit way to fetch the full body.
**Surface:** parameters on the existing send MCP tool + a new dry-run affordance.
**Out:** assertions, suites (later phases).
**Notes:** establishes the compact, structured output contract that Phases 19–21 follow.

### Phase 19 — Assertions & captures (evaluation core)
**Goal:** First-class, declarative checks and value extraction evaluated by the engine.
**Scope:**
- Frontmatter `assertions`: status code, JSONPath value checks, response-time bound, and
  JSON-schema match.
- Frontmatter `captures`: JSONPath → variable name (the foundation for chaining).
- Engine evaluates both on send and returns a **structured result**: per-assertion
  pass/fail with actual-vs-expected, and the captured values.
- Surfaced in the send result (UI + MCP).
**Depends on:** 18 (output conventions). Shares one JSONPath-against-response evaluator
between assertions and captures.
**Out:** running multiple requests together (Phase 20).

### Phase 20 — Suite runs & chaining
**Goal:** Run a sequence of requests as one action with threaded state and an aggregate report.
**Scope:**
- Run a folder/collection of requests in a defined order.
- **Thread captured variables** (Phase 19) from earlier steps into later requests
  (e.g. login token, created id).
- Aggregate **pass/fail report** (per-step + suite total), compact by default.
- Exposed as an MCP `run_suite` tool.
**Depends on:** 19 (assertions + captures).
**Out:** parallel execution, retries/backoff (revisit if needed; YAGNI for now).

### Phase 21 — Snapshot & diff (refactor tool)
**Goal:** Answer "did my change alter the API contract?" without manual file diffing.
**Scope:**
- Baseline a response (reuse the existing history storage as the snapshot source).
- Re-run and produce a **structured diff** of status / headers / body (JSON-aware).
- **Noise filters** to ignore volatile fields (timestamps, request ids, etc.).
- Exposed as an MCP diff tool returning the diff (not two full bodies).
**Depends on:** 18 (output conventions) only.
**Out:** cross-environment matrix diffing (could be a later extension).

## Open questions to resolve per sub-phase (not now)
- Exact frontmatter schema for `assertions`/`captures` (Phase 19).
- JSONPath library choice (Phase 18/19) — pick one and use it consistently.
- Suite definition format: folder convention vs. an explicit suite file (Phase 20).
- Snapshot identity: which history record is "the baseline" and how an agent pins it (Phase 21).

## Out of scope for the whole arc (YAGNI)
- Import (OpenAPI / curl / HAR → request files) — a separate onboarding effort, not part
  of the inner dev loop. Can be its own arc later if wanted.
- Load/perf testing, parallel suite execution.

## Relationship to other work
- Builds on **Phase 17** (sent-request inspector) — Phase 18's dry-run reuses
  `RequestResult.sent`. Phase 17 should land first.
- Independent of the tagged **history-capture accuracy** follow-up, though Phase 21
  (snapshot/diff) would benefit from it (accurate stored requests) — note the synergy when
  scoping Phase 21.
