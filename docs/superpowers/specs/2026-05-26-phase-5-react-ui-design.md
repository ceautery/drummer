# Phase 5: React UI — Design Spec

**Date:** 2026-05-26
**Status:** Approved
**Phase:** 5 — React UI

---

## Overview

Phase 5 builds the complete React frontend for Drummer: a three-panel REST client UI that connects to the Phase 4 FastAPI backend. The deliverable is a fully functional application — open a project, browse requests, send one, see the response — with stub tabs for features that arrive in later phases (scripting, OAuth, GraphQL).

**Build strategy:** Vertical slice. One complete working path (open project → select request → send → see response) is built first to validate the API integration, then the remaining panels and stubs are expanded.

---

## Toolchain & Scaffold

`frontend/` is a new Vite project at the repo root.

### Dependencies

| Tool | Purpose |
|---|---|
| React 19 | UI framework |
| Vite 6 | Build tool |
| TypeScript | Strict mode, `noUncheckedIndexedAccess: true` |
| Tailwind CSS v4 | Styling (CSS-first config, no `tailwind.config.js`) |
| shadcn/ui | Component primitives |
| Zustand 5 | Client state management |
| TanStack Query 5 | Server state + cache |
| CodeMirror 6 | Code editors (URL bar variable highlighting, Body/Script editors) |
| react-resizable-panels | Resizable panel splits |
| lucide-react | Icons |
| Biome | JS/TS linting + formatting (opinionated defaults, no overrides) |
| Playwright | E2E tests |
| Vitest + React Testing Library | Component unit tests |

### Dev mode

`vite.config.ts` proxies `/api` to `http://127.0.0.1:8237`. `npm run dev` starts Vite on port 5173; API calls forward to the running FastAPI server. A new `make dev` Makefile target starts both processes.

### Prod mode

`vite build` outputs to `drummer/api/static/`. FastAPI already serves this directory as a catch-all — no backend changes needed.

### Linting

`biome check --write` is added to `make check` alongside Ruff / Pyright / pytest. All Biome findings must be fixed at the root; no suppression comments.

---

## State & API Layer

### Zustand stores (`frontend/src/store/`)

| Store | Contents |
|---|---|
| `projectStore.ts` | Active project (id, name, path), request tree |
| `requestStore.ts` | Selected request path, editable fields (method, url, params, headers, body, auth, tab), dirty flag, saved snapshot |
| `responseStore.ts` | Latest send result (status, headers, body text, raw bytes, timing, script output), streaming state |
| `sessionStore.ts` | Active environment name, cookie jar summary |

### TanStack Query hooks (`frontend/src/api/`)

| Hook | Endpoint |
|---|---|
| `useProjects()` | `GET /api/projects` |
| `useOpenProject(path)` | `POST /api/projects` |
| `useRequests(projectId)` | `GET /api/projects/{id}/requests` |
| `useRequest(projectId, path)` | `GET /api/projects/{id}/requests/{path}` |
| `useSaveRequest(projectId, path)` | `PUT /api/projects/{id}/requests/{path}` |
| `useEnvironments(projectId)` | `GET /api/projects/{id}/environments` |
| `useEnvironment(projectId, name)` | `GET /api/projects/{id}/environments/{name}` |
| `useSaveEnvironment(projectId, name)` | `PUT /api/projects/{id}/environments/{name}` |
| `useHistory(projectId, requestPath)` | `GET /api/projects/{id}/history` |
| `useCookies()` | `GET /api/cookies` |
| `useClearCookies()` | `DELETE /api/cookies` |
| `useDeleteRequest(projectId, path)` | `DELETE /api/projects/{id}/requests/{path}` |

### SSE send hook (`useSend`)

`POST /api/send` is handled outside TanStack Query via a custom `useSend()` hook. It opens a native `EventSource`, dispatches incremental events to `responseStore` (status + timing arrive first; body streams in; `raw_bytes` on the final event), and cleans up on unmount or cancel. The Send button shows a spinner during streaming; clicking it again cancels the in-flight stream.

---

## Component Structure

```
frontend/src/
├── views/
│   ├── WorkspaceView.tsx      # Main 3-panel layout
│   └── EnvironmentsView.tsx   # Variable editor (stub in Phase 5)
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx        # Project name, env switcher, RequestTree
│   │   └── PanelGroup.tsx     # Resizable split panels (react-resizable-panels)
│   ├── request/
│   │   ├── UrlBar.tsx         # Method selector + URL + Send button
│   │   ├── ParamsTab.tsx      # Query param key/value table
│   │   ├── HeadersTab.tsx     # Header key/value table
│   │   ├── BodyTab.tsx        # Mode switcher: Raw / Form-data / JSON / GraphQL (stub)
│   │   ├── AuthTab.tsx        # None / Bearer / Basic / OAuth (OAuth stub)
│   │   ├── ScriptTab.tsx      # Stub: "Available in Phase 6"
│   │   └── CookiesTab.tsx     # Stub: "Available in Phase 9"
│   ├── response/
│   │   ├── ResponseMeta.tsx   # Status badge + timing + size
│   │   ├── BodyViewer.tsx     # JSON pretty-print / raw text / image
│   │   ├── HeadersViewer.tsx  # Response headers table
│   │   ├── RawViewer.tsx      # Hex dump left + decoded text right
│   │   ├── ScriptOutput.tsx   # Stub: "Available in Phase 6"
│   │   └── HistoryDrawer.tsx  # Last 50 sends for this request
│   ├── tree/
│   │   ├── RequestTree.tsx    # Collapsible folder tree
│   │   └── TreeNode.tsx       # Single node with dirty dot indicator
│   └── shared/
│       ├── VariableChip.tsx   # {{var}} highlight: purple=known, amber=unknown
│       └── StatusBadge.tsx    # 2xx green / 3xx amber / 4xx–5xx red
└── store/
    ├── projectStore.ts
    ├── requestStore.ts
    ├── responseStore.ts
    └── sessionStore.ts
```

---

## Layout

Three-panel layout (Insomnia/Bruno style):

```
┌─────────────┬────────────────────────────────────┐
│             │ UrlBar (method + URL + Send)        │
│  Sidebar    ├────────────────────────────────────┤
│             │ Params │ Headers │ Body │ Auth │... │
│  Project    │                                    │
│  name       │  Request editor                    │
│             │                                    │
│  Env        ├────────────────────────────────────┤
│  switcher   │ Status 200 · 42ms · 1.2kB          │
│             ├────────────────────────────────────┤
│  Request    │ Body │ Headers │ Raw │ Script │ Hist│
│  tree       │                                    │
│             │  Response viewer                   │
│             │                                    │
└─────────────┴────────────────────────────────────┘
```

All three panels are resizable via `react-resizable-panels`. No CSS transitions or animations (speed preference).

---

## Project Opening

On first load (no active project in `projectStore`), the workspace renders a centered card:

- A text input for an absolute filesystem path
- An "Open" button
- Submits `POST /api/projects` with the path
- On success: project loads into `projectStore`, sidebar populates, card replaced by 3-panel workspace
- On error: API error message shown inline below the input

---

## Unsaved Changes

Edits to a request are held in `requestStore` as a dirty copy alongside the saved snapshot.

- A dot indicator appears on the sidebar tree node for the dirty request
- `Cmd+S` (Mac) / `Ctrl+S` calls `PUT /api/projects/{id}/requests/{path}`
- Navigating away from a dirty request shows a browser-native confirm dialog ("Unsaved changes — discard?")
- Saving clears the dirty flag and updates the saved snapshot

---

## Variable Highlighting

`{{variable}}` tokens in the URL bar are rendered by a lightweight CodeMirror 6 extension:

- **Purple chip:** variable is set in the active environment; hover shows the resolved value
- **Amber chip:** variable is not set; hover shows "Not set in [env name]"

The same `VariableChip` component is reused in header values and param values (as a read-only display, not an editor).

---

## Tab Stubs

Tabs for future-phase features are visible and selectable, but show a placeholder message:

| Tab | Message |
|---|---|
| ScriptTab | "Pre/post request scripts — available in Phase 6 (Scripting)" |
| CookiesTab | "Explicit cookie management — available in Phase 9 (OAuth + Cookies)" |
| GraphQL mode (BodyTab) | "GraphQL editor — available in Phase 8 (GraphQL)" |
| OAuth (AuthTab) | "OAuth flow — available in Phase 9 (OAuth + Cookies)" |
| ScriptOutput (response) | "Script console output — available in Phase 6 (Scripting)" |

---

## Testing

### Component unit tests (`frontend/src/**/*.test.tsx`)

Vitest + React Testing Library. Covered:

- `VariableChip`: known variable renders purple + correct tooltip; unknown renders amber
- `StatusBadge`: correct color class for 2xx, 3xx, 4xx, 5xx
- `UrlBar`: method selector cycles through methods; Send button emits correct callback
- Store logic: `requestStore` dirty flag sets on edit, clears on save

### Playwright e2e (`tests/e2e/`)

`playwright.config.ts` at the repo root. `webServer` block launches `drummer serve --project <fixture-project>` before tests.

Three smoke tests:

1. **App loads** — welcome card is visible; `data-testid="welcome-card"` present
2. **Open project** — type a valid project path, click Open → sidebar shows request tree; `data-testid="request-tree"` present
3. **Send request** — click a request → editor populates → click Send → response panel shows a status badge; `data-testid="response-status"` present

All interactive elements carry `data-testid` attributes. These become the contract for Phase 7's tutorial step assertions.

`make e2e` runs Playwright separately; it is not included in `make check` (CI can opt in via `make e2e`).

---

## File Map

| Action | Path |
|---|---|
| Create | `frontend/` — full Vite project |
| Create | `frontend/src/store/*.ts` — four Zustand stores |
| Create | `frontend/src/api/*.ts` — TanStack Query hooks + `useSend` |
| Create | `frontend/src/views/WorkspaceView.tsx` |
| Create | `frontend/src/components/**` — all components listed above |
| Create | `tests/e2e/playwright.config.ts` |
| Create | `tests/e2e/smoke.spec.ts` |
| Modify | `Makefile` — add `dev` target (Vite + FastAPI); add `e2e` target (Playwright); add `cd frontend && biome check` step to `check` target |
| Modify | `pyproject.toml` — no changes needed |
| Modify | `drummer/cli.py` — no changes needed (serve already implemented) |

---

## Out of Scope for Phase 5

- Scripting (Phase 6)
- Mock server and TutorialView (Phase 7)
- GraphQL editor (Phase 8)
- OAuth flow, explicit cookie management, persistent cookie store (Phase 9)
- `EnvironmentsView` (editing variables) — deferred. The sidebar dropdown switches the active environment name in `sessionStore`; it does not open a variable editor. Full variable editing is a Phase 5 stretch goal only if time allows, otherwise Phase 6+.
