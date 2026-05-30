# Drummer Roadmap

| Phase | Description | Status |
|---|---|---|
| 1 — Foundation | Repo scaffold, tooling, CI, ADRs | ✅ Done |
| 2 — Storage | YAML frontmatter parser, project/environment loading | ✅ Done |
| 3 — HTTP engine | Request send, variable substitution, cookie jar, encoding | ✅ Done |
| 4 — API + MCP | FastAPI app, REST routes, MCP tools, response history | ✅ Done |
| 5 — React UI | Vite scaffold, workspace view, request editor, response viewer | ✅ Done |
| 6 — Scripting | QuickJS runner, dm API, script debugger | ✅ Done |
| 7 — Mock server + tutorial | Met dataset, mock routes, TutorialView | ✅ Done |
| 8 — GraphQL | GraphQL query building, introspection, BodyTab mode | ✅ Done |
| 9 — OAuth + cookies | OAuth flow handler, persistent cookie store | ✅ Done |
| 10 — Distribution | Homebrew formula, make dist, docs site | ✅ Done |
| 11 — Workspaces | Central `~/.drummer` storage, Scratch catchall, external folders, bare `drummer` launches, top-bar workspace switcher | ✅ Done |
| 12 — Theming | Dark / light / system-auto toggle across the app and tutorial | ✅ Done |
| 13 — Tutorial cohesion | Tutorial drives the real request/response panes; unified Workspace/Tutorial tabs in the AppBar | ✅ Done |
| 14 — Wikidata GraphQL | Wikidata GraphQL dataset + GraphQL tutorial step | ✅ Done |

## Post-1.0 Hardening Arc

Spec: `docs/superpowers/specs/2026-05-29-post-1.0-hardening-arc-design.md`.
Plan for the first slice: `docs/superpowers/plans/2026-05-29-fixes-and-phase-15-request-editing.md`.

| Item | Description | Status |
|---|---|---|
| F1 — Raw tab | Raw response tab is a pure hexdump (dropped redundant body panel) | ✅ Done |
| F2 — Forget external workspace | `forget_external` core fn + `POST /workspaces/forget` + switcher action; e2e server `DRUMMER_HOME` isolated so fixtures no longer pollute the real registry | ✅ Done |
| 15 — Request editing & CRUD | **Critical save fix** (PUT round-trips the full request → no more silent auth/params/script loss or white-screen crash), visible Save button, new/delete requests in the tree | ✅ Done (verified in-app) |
| 16 — Environment & variable editor | Create/delete environments + a per-environment variable table editor (today the UI only selects environments; there's no way to set `{{base_url}}` from the app) | ✅ Done (verified in-app) |
| 17 — Sent-request inspector | A "Sent" response tab showing the truly-sent request (final URL, params, headers with auth masked, body, variables used) + a persistent unresolved-variable warning banner | 📋 Spec + plan ready, not yet implemented |

Phase 17 spec: `docs/superpowers/specs/2026-05-30-phase-17-sent-request-inspector-design.md`.
Phase 17 plan: `docs/superpowers/plans/2026-05-30-phase-17-sent-request-inspector.md`.

**Deferred / follow-up:**
- **History capture accuracy** (tagged during Phase 17): the history DB record stores the *resolved* (pre-mutation) headers/body, omits query params, and stores the response URL. Follow-up: add a `request_params` column, persist the truly-sent request into history, and show params in the HistoryDrawer. Needs a DB schema change, so it's deferred out of Phase 17.
- Request file **rename** and **move/folders** in the tree (and environment **rename**) — these share a "move file" primitive, best done together in a later phase. (Editing a request's display name already works through the normal save path.)

## Agent API Toolkit Arc (planned)

Make Drummer a better-than-curl tool for an AI agent refactoring and testing APIs (driven over MCP).
Arc design: `docs/superpowers/specs/2026-05-30-agent-api-toolkit-arc-design.md`. Each sub-phase gets
its own spec/plan. Dependency chain 18 → 19 → 20; 21 after 18.

| Phase | Description | Status |
|---|---|---|
| 18 — Agent-ergonomic send | Dry-run (resolved request, no send), JSONPath field extraction, body truncation/summarization — compact MCP output that doesn't flood agent context | ⏳ Planned (arc spec only) |
| 19 — Assertions & captures | Declarative frontmatter assertions (status/JSONPath/time/schema) + captures (JSONPath → variable); engine returns structured pass/fail | ⏳ Planned (arc spec only) |
| 20 — Suite runs & chaining | Run a folder in order, thread captured variables between steps, aggregate report via an MCP `run_suite` tool | ⏳ Planned (arc spec only) |
| 21 — Snapshot & diff | Baseline a response, re-run after a change, structured contract diff with noise filters | ⏳ Planned (arc spec only) |

Out of scope for the arc: import (OpenAPI/curl/HAR), load testing, parallel execution.

