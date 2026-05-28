# Phase 7 Design: Mock Server + Tutorial

**Date:** 2026-05-27  
**Status:** Approved

## Overview

Phase 7 adds three things to Drummer:

1. **Met snapshot** — a bundled JSON file with ~25 Metropolitan Museum artworks
2. **Mock routes** — a FastAPI router at `/mock/met/...` that serves the snapshot
3. **TutorialView** — a 7-step guided walkthrough UI built on top of the mock routes

The goal is a self-contained, offline-capable tutorial that teaches Drummer's core features (GET requests, path/query params, variables, scripting) using real-looking data from the Met collection.

---

## Dataset & Mock Routes

### Snapshot file

`drummer/api/mock/met_snapshot.json` — committed to the repo, loaded at module import (not per-request).

Format:
```json
{
  "departments": [
    { "departmentId": 1, "displayName": "American Decorative Arts" },
    ...
  ],
  "objects": {
    "45734": {
      "objectID": 45734,
      "title": "Self-Portrait with a Straw Hat",
      "artistDisplayName": "Vincent van Gogh",
      "department": "European Paintings",
      "objectDate": "1887",
      "medium": "Oil on canvas",
      "dimensions": "15 7/8 × 12 3/8 in. (40.3 × 31.4 cm)",
      "isHighlight": true,
      "isPublicDomain": true,
      "accessionNumber": "67.187.70a"
    },
    ...
  }
}
```

25 objects across 5 departments (5 per department): American Decorative Arts, European Paintings, Egyptian Art, Modern and Contemporary Art, Asian Art. Object fields mirror the real Met API response shape.

No new Python dependencies — loaded with stdlib `json` + `pathlib`.

### FastAPI router

`drummer/api/routes/mock.py`, mounted at `/mock/met` in `app.py`.

| Method | Path | Response |
|--------|------|----------|
| GET | `/mock/met/departments` | `{ "departments": [...] }` |
| GET | `/mock/met/objects` | `{ "total": N, "objectIDs": [...] }` — optional `departmentIds` query param (comma-separated ints) |
| GET | `/mock/met/objects/{id}` | Full object dict; HTTP 404 if not in snapshot |
| GET | `/mock/met/search` | `{ "total": N, "objectIDs": [...] }` — `?q=` filters title/artistDisplayName/medium case-insensitively |

---

## Tutorial Steps

Step specs are defined as a Python list of typed dataclasses in `drummer/api/routes/tutorial.py`. No `.md` files — specs live in Python.

`POST /api/tutorial/steps/{n}/send` constructs a `RequestFile` from the step spec, calls `resolve()` + `engine.send()`, and streams SSE back — identical pipeline to the regular send route. Variable overrides for steps that use `{{base_url}}` are embedded in the step spec.

### Step sequence

| # | Title | What it teaches | Request |
|---|-------|-----------------|---------|
| 1 | Welcome to Drummer | Tool overview, Met tutorial intro | — (no Send button) |
| 2 | Your first GET request | Basic HTTP GET, reading JSON responses | `GET /mock/met/departments` |
| 3 | Path parameters | Fetching a specific resource by ID | `GET /mock/met/objects/45734` |
| 4 | Query parameters | Filtering via `?q=` | `GET /mock/met/search?q=sunflowers` |
| 5 | Environment variables | `{{base_url}}` substitution, reusable configs | `GET {{base_url}}/mock/met/departments` with `base_url=http://localhost:8000` override |
| 6 | Pre-request scripts | Mutating the request before send | `GET /mock/met/objects/45734` with pre-script setting `X-Tutorial-Id` header |
| 7 | Post-request scripts | Reading and logging the response | `GET /mock/met/objects/45734` with post-script doing `dm.console.log(dm.response.json().title)` |

---

## TutorialView UI

### Layout

Two-column split, full-screen view replacing WorkspaceView when active.

```
┌─────────────────────────────────────────────────────────────┐
│ 🥁 Drummer   Workspace   Tutorial                           │  ← App nav
├──────────────────────┬──────────────────────────────────────┤
│ PROGRESS             │ REQUEST                              │
│  ✓ Welcome           │  GET  http://localhost:8000/mock/... │
│  ✓ First GET         │                          [Send ▶]    │
│  ▶ Path parameters   ├──────────────────────────────────────┤
│  ○ Query params      │ RESPONSE                             │
│  ○ Variables         │  200 OK  ·  18ms                     │
│  ○ Pre-script        │  {                                   │
│  ○ Post-script       │    "objectID": 45734,                │
│                      │    "title": "Self-Portrait...",      │
│ INSTRUCTIONS         │    ...                               │
│  [prose + snippets]  │  }                                   │
│                      │                                      │
│  [← Back]  [Next →]  │                                      │
└──────────────────────┴──────────────────────────────────────┘
```

### Components

- `frontend/src/views/TutorialView.tsx` — top-level view; owns `currentStep` and `completedSteps` state
- Left column: step list (with ✓/▶/○ indicators) + instructions panel + Back/Next buttons
- Right column: request card (method badge + URL display + Send button) + response panel (status, elapsed, JSON body)

### State

- `currentStep: number` — zero-indexed, local to TutorialView
- `completedSteps: Set<number>` — marked complete on Next click; persists for the session
- `response: TutorialResponse | null` — last SSE result for the current step (status, elapsed, body, script logs/error)
- TutorialView does **not** touch `requestStore` or `responseStore` — fully self-contained

### Step 1 (Welcome)

No request card. No Send button. Instructions fill the right column. Next button advances immediately.

### Script output (Steps 6 & 7)

The response panel gains a script output section below the body: `dm.console.log` output shown in amber, script errors in red, suggestions in amber italic.

---

## Navigation Integration

`App.tsx` adds a `view` state: `"workspace" | "tutorial"`. The top nav bar renders two links; clicking switches the view. No routing library — plain conditional render. The nav is already present in the existing layout; we add one entry.

---

## New Files

| Action | Path |
|--------|------|
| Create | `drummer/api/mock/met_snapshot.json` |
| Create | `drummer/api/routes/mock.py` |
| Create | `drummer/api/routes/tutorial.py` |
| Modify | `drummer/api/app.py` — mount mock router + tutorial router |
| Create | `frontend/src/views/TutorialView.tsx` |
| Modify | `frontend/src/App.tsx` — add view state + Tutorial nav entry |
| Create | `tests/unit/test_mock_routes.py` |
| Create | `tests/integration/test_mock_routes.py` |
| Create | `tests/integration/test_tutorial_route.py` |

---

## Testing

### Unit tests (`tests/unit/test_mock_routes.py`)

- Departments endpoint returns correct count
- Object endpoint returns correct object by ID
- Object endpoint returns 404 for unknown ID
- Search filters by query string (case-insensitive)
- Objects endpoint filters by `departmentIds`

### Unit tests (`tests/unit/test_tutorial.py`)

- All 7 step specs are well-formed (have required fields)
- Steps with requests have non-empty method and URL
- Steps with scripts have non-empty script strings

### Integration tests (`tests/integration/test_mock_routes.py`)

- `GET /mock/met/departments` → 200, `departments` array present
- `GET /mock/met/objects/45734` → 200, correct title
- `GET /mock/met/objects/99999` → 404
- `GET /mock/met/search?q=van+gogh` → 200, objectIDs includes 45734

### Integration tests (`tests/integration/test_tutorial_route.py`)

Steps are 0-indexed in the API (`/steps/0` = Welcome, `/steps/1` = first GET, etc.).

- `POST /api/tutorial/steps/1/send` → SSE `done` event with no script error (step index 1 — "Your first GET request")
- `POST /api/tutorial/steps/5/send` → SSE `done` event, pre-script header mutation applied (step index 5 — "Pre-request scripts")
- `POST /api/tutorial/steps/6/send` → SSE `done` event, post-script log contains artwork title (step index 6 — "Post-request scripts")

### Frontend

No new Vitest tests. TutorialView is a pure rendering component; send behavior is covered by backend integration tests.

---

## Out of Scope for Phase 7

- Tutorial progress persistence across sessions (localStorage or backend)
- User-editable request fields within TutorialView
- Deep-linking to a specific tutorial step via URL
- Any GraphQL, OAuth, or cookie tutorial steps (those belong to Phases 8–9)
