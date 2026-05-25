# Drummer — Design Spec

**Date:** 2026-05-25
**Status:** Approved

---

## Overview

Drummer is a standalone, local REST client application — a free, open alternative to Postman, Insomnia, and Bruno. It runs as a local web app (Python backend + React frontend) with no login, no subscription, and no phone-home. The user owns their data forever.

Primary target: macOS. Secondary: Linux/BSD with minimal friction. Distributed via Homebrew.

---

## Name & Identity

**Drummer** — chosen for the cadence/rhythm theme without being too abstract. Unclaimed in dev tooling (no Homebrew formula, no significant npm/PyPI package).

---

## Architecture

### Approach: Layered monorepo

Three clear layers in one git repository:

```
drummer/                          # Repo root
├── drummer/                      # Python package (installable)
│   ├── core/                     # HTTP engine — no web framework dependency
│   │   ├── engine.py             # Sends requests, returns structured responses
│   │   ├── variables.py          # Variable substitution + environment resolution
│   │   ├── cookies.py            # Cookie jar (session / disabled / explicit modes)
│   │   ├── encoding.py           # Charset detection and encoding/decoding
│   │   ├── graphql.py            # GraphQL query building + introspection
│   │   ├── scripting.py          # QuickJS runner: pre/post request scripts
│   │   ├── debugger.py           # Script failure analysis + actionable suggestions
│   │   └── storage/
│   │       ├── project.py        # Load/save projects (YAML frontmatter files)
│   │       └── formats.py        # Parse .md request files, validate schema
│   ├── api/                      # FastAPI app
│   │   ├── app.py                # App factory, mounts MCP, serves static
│   │   ├── routes/               # REST endpoints for the UI
│   │   └── mcp/                  # MCP server tools
│   ├── mock/                     # Built-in mock server + bundled CC dataset
│   └── cli.py                    # `drummer` entrypoint
├── frontend/                     # React + Vite (compiled to drummer/api/static/)
│   ├── src/
│   │   ├── views/
│   │   ├── components/
│   │   └── store/
│   └── vite.config.ts
├── tests/
│   ├── unit/                     # pytest, no server, no DB
│   ├── integration/              # pytest + real FastAPI test client + in-memory SQLite
│   └── e2e/                      # Playwright, full running instance
├── docs/
│   ├── decisions/                # Architecture Decision Records (ADRs)
│   ├── specs/                    # Brainstorming design docs (here)
│   └── tutorial/                 # User-facing tutorial content
├── TODO.md
├── ROADMAP.md
├── CLAUDE.md
└── pyproject.toml
```

### Process model

`drummer serve` starts one FastAPI/Uvicorn process. In production mode it serves compiled React from `drummer/api/static/`. In dev mode, Vite runs on a separate port with a proxy to FastAPI. The MCP server mounts as a sub-application at `/mcp`.

### Key dependencies

| Purpose | Library |
|---|---|
| Backend framework | FastAPI + Uvicorn |
| HTTP client | `httpx` (async, HTTP/1.1 + HTTP/2) |
| Scripting engine | `python-quickjs` |
| YAML frontmatter | `python-frontmatter` |
| Data validation | Pydantic v2 |
| Database | SQLite via `aiosqlite` + SQLAlchemy (async) |
| MCP server | `mcp` SDK or `fastapi-mcp` |
| Python linting | Ruff (strict) + Pyright (strict) |
| JS linting | Biome (opinionated defaults) |
| Testing | Pytest + `pytest-asyncio` + Playwright |
| Frontend | React 19 + Vite + Tailwind v4 + shadcn/ui |
| State management | Zustand |
| Resizable panels | `react-resizable-panels` |
| Code editor | CodeMirror 6 |
| API hooks | TanStack Query |
| Icons | `lucide-react` |

---

## Data Model

### File system (git-tracked)

Every project is a folder. All request definitions, environments, and metadata live as human-readable files — fully diffable and exportable.

```
my-api-project/
├── .drummer/
│   ├── project.yaml
│   └── environments/
│       ├── local.yaml
│       ├── staging.yaml
│       └── prod.yaml
├── auth/
│   └── login.md
├── users/
│   ├── list-users.md
│   └── create-user.md
└── README.md
```

**`project.yaml`**
```yaml
name: My API Project
version: "1"
default_environment: local
```

**`environments/local.yaml`**
```yaml
name: local
variables:
  base_url: http://localhost:3000
  token: ""
```

**Request file format (YAML frontmatter + Markdown body)**
```markdown
---
name: List Users
method: GET
url: "{{base_url}}/api/users"
headers:
  Authorization: "Bearer {{token}}"
params:
  page: "1"
  limit: "20"
encoding: utf-8
cookies:
  mode: session          # session | disabled | explicit
auth:
  type: bearer
  token: "{{token}}"
pre_script: |
  dm.env.set("ts", Date.now().toString());
post_script: |
  const body = dm.response.json();
  dm.env.set("first_user_id", body.users[0].id);
tags: [users, list]
skip: false
---

Fetches a paginated list of users. Requires `{{token}}` set in the active environment.
```

**GraphQL requests** use the same format with an additional `graphql` block:
```yaml
graphql:
  query: |
    query GetUser($id: ID!) {
      user(id: $id) { name email }
    }
  variables:
    id: "{{user_id}}"
```
The body field is unused; the `graphql` block serializes to `{"query": ..., "variables": ...}` as `application/json`.

### SQLite (not git-tracked, `~/.local/share/drummer/`)

| Table | Purpose |
|---|---|
| `response_history` | Per-request log: timestamp, status, duration, response snapshot (capped at 50/request) |
| `cookie_store` | Persistent cookies keyed by domain + path |
| `app_state` | Last-open project, active environment, UI preferences |

### Variable scoping (resolution order)

1. Request-level inline overrides
2. Active environment (`environments/*.yaml`)
3. Global variables (`~/.config/drummer/globals.yaml`)

Missing variables render as `{{name}}` (not an error) and surface as warnings in the result.

---

## Core HTTP Engine

### Send pipeline

```
load request file → resolve variables → build httpx request
  → run pre_script → send (recording transport) → run post_script
  → store response history → return RequestResult
```

The engine takes a `ResolvedRequest` Pydantic model in and returns a `RequestResult` out. No FastAPI, no UI dependencies — purely callable from tests, MCP tools, and scripts.

### Cookie jar

| Mode | Behavior |
|---|---|
| `session` | Cookies accumulate across requests in a session (like a browser) |
| `disabled` | No cookies sent or stored |
| `explicit` | Only cookies listed inline in the request file |

Persistent cookies (future-expiry `Set-Cookie`) are written to SQLite `cookie_store`. Session cookies live in memory, cleared on session end or explicit user action.

### Encoding

- **Request body:** charset from request file (default UTF-8); body encoded before send
- **Response:** charset from `Content-Type` header; falls back to `chardet` auto-detection
- **Supported:** all Python `codecs` charsets — UTF-8/16/32, Latin-1, Windows-1252–1258, ISO-8859 family, Shift-JIS, GBK, and more
- EBCDIC: deferred to v2

### Byte-level network recording

A custom `httpx` transport wrapper captures raw bytes sent and received. Stored as binary blobs in `response_history`. Viewable in the UI as hex dump + decoded text side-by-side.

### QuickJS scripting (`dm` API)

| API | Description |
|---|---|
| `dm.env.get(key)` / `dm.env.set(key, val)` | Read/write active environment variables |
| `dm.request.*` | Mutable request object (pre-script only) |
| `dm.response.status` | HTTP status code |
| `dm.response.json()` | Parsed response body |
| `dm.response.text()` | Raw response body as string |
| `dm.response.headers` | Response header map |
| `dm.console.log(...)` | Captured and shown in script output panel |

Script timeout: 5 seconds. All `console.log` output is captured even if the script fails.

### Script debugger

Pattern-matching registry of `(failure pattern → actionable suggestion)`:

| Pattern | Suggestion |
|---|---|
| `TypeError: undefined is not an object` | "Response may not be JSON — check Content-Type. Try logging `dm.response.text()` first." |
| `dm.env.get('X')` returns null | "Variable 'X' is not set in the active environment. Add it under Environments." |
| Script timeout | "Script timed out after 5s. Check for infinite loops." |
| Parse error | Shows exact line/column with code snippet highlighted. |
| Uncaught exception | Full QuickJS stack trace, formatted and syntax-highlighted. |

New patterns are added as a registry entry — no structural changes required.

---

## API Layer

### REST routes

```
/api/projects                          GET, POST
/api/projects/{id}                     GET, DELETE
/api/projects/{id}/requests            GET (tree), POST
/api/projects/{id}/requests/{path}     GET, PUT, DELETE
/api/projects/{id}/environments        GET
/api/projects/{id}/environments/{name} GET, PUT
/api/projects/{id}/history            GET
/api/send                             POST (streams SSE)
/api/cookies                          GET, DELETE
/api/oauth/start                      GET
/api/oauth/callback                   GET
/mcp                                  MCP sub-application
/                                     React (catch-all)
```

`POST /api/send` streams server-sent events: status + timing arrive as soon as headers are received; body streams in; final event includes the raw byte recording.

**OAuth flow:** `/api/oauth/start` opens the system browser to the authorization URL. `/api/oauth/callback` captures the code, exchanges it for a token, and injects it into the active environment — no manual copy-paste.

### API layer rules

- All endpoints return typed Pydantic response models — no untyped dicts
- Errors return `{"error": "...", "detail": "..."}` consistently
- The API layer never touches files directly — it calls `drummer/core/storage`
- No business logic in route handlers

### MCP tools

| Tool | Description |
|---|---|
| `list_projects` | All known projects with metadata |
| `list_requests` | Request tree for a project |
| `get_request` | Parsed definition of a request |
| `create_request` | Creates a new `.md` request file |
| `update_request` | Updates fields in an existing request |
| `send_request` | Fires a request; returns status, headers, body, timing, script output |
| `get_history` | Recent response history for a request |
| `list_environments` | Environments for a project |
| `get_variables` | Variables for a named environment |
| `set_variable` | Sets a variable in the active environment |
| `switch_environment` | Changes the active environment |
| `clear_cookies` | Clears the session cookie store |

Claude connects to `http://localhost:{port}/mcp`. Typical Claude workflow: `list_projects` → `list_requests` → `get_request` → `send_request` → inspect → `set_variable` → `send_request` again.

---

## Frontend

### Layout: Stacked (Insomnia/Bruno style)

Sidebar left (project tree + environment switcher). Main area: request editor top, response viewer bottom — both visible simultaneously. Resizable via `react-resizable-panels`.

### Component structure

```
frontend/src/
├── views/
│   ├── WorkspaceView.tsx      # Main 3-panel layout
│   ├── EnvironmentsView.tsx   # Variable editor
│   ├── HistoryView.tsx        # Full response history log
│   └── TutorialView.tsx       # Built-in tutorial shell
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx        # Project tree + environment switcher
│   │   └── PanelGroup.tsx     # Resizable split panels
│   ├── request/
│   │   ├── UrlBar.tsx         # Method selector + URL + Send button
│   │   ├── ParamsTab.tsx
│   │   ├── HeadersTab.tsx
│   │   ├── BodyTab.tsx        # Raw / form-data / JSON / GraphQL modes
│   │   ├── AuthTab.tsx        # None / Bearer / Basic / OAuth
│   │   ├── ScriptTab.tsx      # Pre/post CodeMirror editors
│   │   └── CookiesTab.tsx     # Mode selector + explicit cookie list
│   ├── response/
│   │   ├── ResponseMeta.tsx   # Status badge, timing, size
│   │   ├── BodyViewer.tsx     # JSON pretty-print / raw / image
│   │   ├── HeadersViewer.tsx
│   │   ├── RawViewer.tsx      # Hex dump + decoded text side-by-side
│   │   ├── ScriptOutput.tsx   # console.log + debugger messages
│   │   └── HistoryDrawer.tsx  # Recent sends for this request
│   ├── tree/
│   │   ├── RequestTree.tsx
│   │   └── TreeNode.tsx
│   └── shared/
│       ├── VariableChip.tsx   # {{variable}} inline highlighting
│       └── StatusBadge.tsx    # 2xx green / 4xx amber / 5xx red
└── store/
    ├── projectStore.ts
    ├── requestStore.ts
    ├── responseStore.ts
    └── sessionStore.ts
```

### Key UI behaviors

- **Variable highlighting:** `{{name}}` tokens in the URL bar render as purple chips (known) or amber chips (unknown). Resolved value shown on hover.
- **Live send feedback:** Response panel streams SSE — status + timing appear when headers arrive, body streams in.
- **Unsaved changes:** Edits held in Zustand; dot indicator on sidebar node; Cmd+S saves; navigation prompts if unsaved.
- **JSON unwrapping:** Detects double-encoded JSON fields; one-click unwrap to pretty-print the inner value.
- **Request skipping:** `skip: true` in the request file renders with strikethrough in sidebar; excluded from collection runs.
- **No animations/transitions:** UI preference is speed over flash. No CSS transitions on panel resizes, tab switches, or state changes.

---

## Mock Server & Tutorial

### Dataset: Metropolitan Museum of Art Open Access (CC0)

~2,000 artwork records bundled as static JSON. Rich metadata: title, artist, department, medium, date, culture, dimensions. Served fully offline — no network call, no API key.

**Mock API endpoints:**
```
GET /mock/departments
GET /mock/departments/{id}
GET /mock/departments/{id}/artworks
GET /mock/artworks
GET /mock/artworks/{id}
GET /mock/search?q=&department=
```

Responses include realistic pagination, varying sizes, and deliberate quirks that exercise Drummer's features.

### Tutorial steps

| Step | Skill taught |
|---|---|
| 1 | What Drummer is; start the mock server |
| 2 | Send first request: `GET /mock/departments` |
| 3 | Set `base_url` variable; use it in the URL |
| 4 | Post-script: extract a department ID from the response |
| 5 | Linked request: `GET /mock/departments/{{dept_id}}/artworks` |
| 6 | Query params: `page` and `limit` |
| 7 | Headers: add `X-Tutorial-Key`; see it echoed back |
| 8 | Script editor: pre-script logs timestamp; post-script extracts first artwork title |
| 9 | Raw tab: identify headers and body boundary in the byte view |
| 10 | Graduation: summary + "Open a real project" CTA |

Tutorial steps carry `data-` attributes for Playwright assertion.

### Attribution

The Met dataset credit appears in:
1. Tutorial step 1 — full attribution block with license (CC0) and link
2. `docs/tutorial/credits.md` — dedicated credits page
3. `drummer/mock/DATA_ATTRIBUTION.md` — ships with the package; surfaced by `drummer --attribution`

---

## Testing & Linting

### Test layers

| Layer | Scope | Speed |
|---|---|---|
| `tests/unit/` | `drummer/core` only — no server, no DB | Fast (<5s) |
| `tests/integration/` | All API endpoints + MCP tools; real FastAPI test client + in-memory SQLite; httpx transport mocked | Medium |
| `tests/e2e/` | Full running Drummer instance + Playwright; tutorial flow, main workflow, OAuth (mocked), script editor | Slow (CI only) |

Pre-commit hook: `ruff check . && biome check . && pyright . && pytest tests/unit tests/integration`

### Linting rules

- **Ruff**: strict mode, all checks enabled
- **Biome**: opinionated defaults, no overrides without justification
- **Pyright**: strict mode
- **No `# noqa`, no `// eslint-disable`, no Pyright suppression comments.** Fix the root cause. Doing things right is always in scope.

---

## CLI & Distribution

```
drummer serve              # Start server, open browser
drummer serve --port 8742  # Custom port
drummer new <path>         # Create a new project
drummer export <path>      # Zip a project for sharing
drummer mcp                # Print MCP server URL and tool list
drummer --attribution      # Print dataset credits
```

**Homebrew:** Formula in a `homebrew-drummer` tap repo. Installs Python package in a managed venv. `make dist` builds the wheel, updates formula SHA256, opens tap PR.

**Linux:** `pip install drummer` or the same Homebrew tap.

---

## Project Management

```
docs/decisions/            # ADRs — record why, not just what
  001-quickjs-scripting.md
  002-yaml-frontmatter-format.md
  ...
docs/specs/                # Brainstorming design docs
TODO.md                    # Current sprint only — nothing backlogged here
ROADMAP.md                 # High-level milestone view
```

ADR required before any decision that changes a layer boundary.

### CLAUDE.md directives

- Default to subagent-driven development (superpowers skill) unless the task is trivial
- All commits must pass Ruff + Biome + Pyright + `tests/unit` + `tests/integration`
- Fix linting and type errors at the root — no suppression comments
- ADR required for layer boundary changes
- Keep work concise, documented, and interruptable

---

## Subsystem Build Order

| Phase | Deliverable |
|---|---|
| 1 — Foundation | Repo scaffold, `pyproject.toml`, linting config, CLAUDE.md, CI skeleton, ADR #001–002 |
| 2 — Storage | `core/storage/` — parse/write YAML frontmatter files, project + environment loading |
| 3 — HTTP engine | `core/engine.py`, variable substitution, cookie jar, encoding, basic send |
| 4 — API + MCP | FastAPI app, all REST routes, MCP tools, SQLite response history |
| 5 — React UI | Vite scaffold, WorkspaceView, request editor, response viewer, Zustand stores |
| 6 — Scripting | QuickJS runner, `dm` API surface, script debugger |
| 7 — Mock server + tutorial | Met dataset extract, mock routes, TutorialView |
| 8 — GraphQL | `core/graphql.py`, BodyTab GraphQL mode, introspection |
| 9 — OAuth + advanced cookies | OAuth flow handler, explicit cookie mode, persistent cookie store |
| 10 — Distribution | Homebrew formula, `make dist`, docs site |

---

## Out of Scope (v1)

- EBCDIC encoding
- gRPC
- WebSocket support (flag for v2)
- Response diffing (flag for v2)
- Team sharing / collaboration
