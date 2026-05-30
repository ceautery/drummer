# TODO

## Post-1.0 hardening arc

**Done (committed, pushed, tree green):**
- F1 — Raw response tab is a pure hexdump.
- F2 — Forget external workspace (core + route + switcher action) and e2e `DRUMMER_HOME` isolation.
- Phase 15 — critical save data-loss/crash fix, visible Save button, new/delete requests in the tree. Verified in-app.
- Phase 16 — environment & variable editor (backend create/delete, Dialog primitive, EnvironmentManager
  modal from a sidebar gear button). Verified in-app.

- Phase 17 — Sent-request inspector: "Sent" response tab (truly-sent URL/params/headers with
  auth+cookie masked/body/variables) + a persistent unresolved-variable warning banner. Verified
  in-app (substituted URL, masked auth header, banner names stray vars).

**Post-1.0 hardening arc is COMPLETE** (F1, F2, Phases 15–17). Next up: the Agent API Toolkit arc (below).

## Follow-up work (tagged, not yet planned)
- **History capture accuracy** (tagged during Phase 17 design): the history DB record
  (`ResponseHistoryRecord`) stores the *resolved* (pre-mutation) headers/body, **omits query
  params**, and stores the response URL rather than the substituted request URL. Follow-up:
  add a `request_params` column (DB schema change), persist the truly-sent request
  (`RequestResult.sent`, available after Phase 17) into the history record, and surface params
  in the `HistoryDrawer`. Deferred out of Phase 17 because it needs a schema migration.
- **Secret variable values shown in the Sent tab** (noticed during Phase 17 verification): the
  Authorization/Cookie headers are masked, but a secret-bearing variable (e.g. `token`) shows its
  value in the "Variables used" section. Acceptable for a local single-user tool; a future hardening
  could mask known-secret variable names.

## Agent API Toolkit arc (in progress)
Arc design: `docs/superpowers/specs/2026-05-30-agent-api-toolkit-arc-design.md`.
- **Phase 18 — agent-ergonomic send: DONE** (verified). `POST /api/agent/send` (clean JSON MCP tool):
  dry-run, JSONPath extraction (jsonpath-ng), body truncation, structured result with sent request +
  warnings + script errors. Spec/plan: `docs/superpowers/{specs,plans}/2026-05-30-phase-18-agent-ergonomic-send*.md`.
- **Next:** Phase 19 (assertions & captures) → 20 (suite runs & chaining) → 21 (snapshot & diff). Each needs its own spec → plan.

### Phase 18 follow-ups (minor)
- Extract the triplicated `_safe_path` helper (`send.py` / `agent.py` / `mcp/tools.py`) into one shared util.
- Add an integration test for the agent route's 502 (transport-error) path.

## Deferred
- Request file **rename** + environment **rename** + tree **move/folders** — shared "move file" primitive, a later phase.

## Known gap to address in a future cleanup
- `make check` runs Biome + tsc + the Python test suite, but NOT the frontend vitest suite — so broken
  frontend tests pass the pre-commit gate. Worth wiring `npm run test` (vitest run) into `make check`.
