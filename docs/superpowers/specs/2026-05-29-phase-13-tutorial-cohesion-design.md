# Phase 13 — Tutorial Cohesion

**Status:** Approved design — ready for implementation plan
**Date:** 2026-05-29
**Author:** brainstormed with Claude

## Context

The tutorial is currently a separate full-screen view. `App.tsx` does
`if (view === "tutorial") return <TutorialView/>`, swapping out the entire shell —
including the persistent `AppBar`. `TutorialView` renders its **own** nav bar (logo +
Workspace/Tutorial buttons + a duplicate `ThemeToggle`), a **bespoke request card** (a
hardcoded `STEPS` array with `displayMethod`/`displayUrl` and a custom SSE `handleSend`
calling `/api/tutorial/steps/{i}/send`), and reuses only the shared
`ResponseMeta`/`BodyViewer`/`ScriptOutputView` components.

This phase makes the tutorial cohesive with the rest of the app: one persistent app bar
with Workspace/Tutorial tabs, and the tutorial driving the **real** request/response panes
instead of its bespoke card. It also clears the Phase 12 carry-over: a duplicate
`ThemeToggle` was deliberately added to both the `AppBar` and `TutorialView`'s own nav, to
be consolidated here.

This is the third of the post-10 arc (11 Workspaces → 12 Theming → 13 Tutorial cohesion →
14 Wikidata GraphQL). The Phase 11 spec explicitly deferred the Workspace/Tutorial app-bar
tabs to this phase.

## Goals

- One **persistent `AppBar`** across both modes, with **Workspace / Tutorial tabs**.
- The tutorial **drives the real request & response panes** (real `UrlBar`, request tabs,
  response tabs/viewers) instead of its bespoke card.
- **Remove the duplicate `ThemeToggle`** from `TutorialView`; one toggle lives in the AppBar.
- The tutorial's step content becomes a **single source of truth** on the backend (no
  duplicated step array in the frontend).

## Non-goals

- **Project/tree pane in the tutorial.** The chosen layout (A) uses the coach rail's step
  list as the navigation; there is no request tree during the tutorial. The ROADMAP's
  "project pane steps" wording is dropped (see Docs).
- **Hands-on / coached editing.** Interaction model is *preloaded + real Send (guided)*:
  each step preloads its request into the real panes and the user clicks the real Send
  button. Editing the preloaded request is technically possible (the real tabs are live)
  but is not required to advance and is ephemeral.
- **Routing the tutorial through the real `/api/send` pipeline.** The existing
  `/api/tutorial/steps/{i}/send` endpoint is kept (it already handles the in-app mock
  transport, variable overrides, and no history pollution); only its results are rendered
  through the real `responseStore`.
- Backend mock Met routes, the step dataset content, and OAuth/cookie behavior are unchanged.

## Key decisions

| Decision | Choice |
|---|---|
| Interaction model | **Preloaded + real Send (guided)** |
| Coach placement | **Layout A** — coach as the left rail; real request/response panes on the right; no request tree |
| Project-pane goal | **Dropped** — reword the ROADMAP Phase 13 line |
| Send pipeline | **Reuse `/api/tutorial/steps/{i}/send`**, rendered through the real `responseStore` |
| Component reuse | **Shared `RequestResponseWorkbench`** read from singleton stores; `TutorialView` snapshots/restores those stores to avoid bleed |
| Step content source | **Backend `GET /api/tutorial/steps`** — single source of truth |

## Architecture

One persistent shell. `App.tsx` always renders `<AppBar/>`, then renders the active view
below it:

```
App
├── AppBar  (persistent: logo · Workspace/Tutorial tabs · WorkspaceSwitcher · ThemeToggle)
└── body
      ├── view === "tutorial"  →  TutorialView  =  [ Coach rail ][ RequestResponseWorkbench ]
      └── view === "workspace" →  WorkspaceView  =  [ Sidebar tree ][ RequestResponseWorkbench ]
```

### App.tsx gating

```
if (settingsLoading) → "Loading…"
render:
  <div class="flex h-screen flex-col">
    <AppBar/>
    <div class="min-h-0 flex-1">
      { view === "tutorial"  ? <TutorialView/>
        : isLoading          ? <Loading/>          // project still loading
                             : <WorkspaceView/> }
    </div>
  </div>
```

The tutorial no longer blocks on the project (active-workspace) load; the workspace path
keeps its existing `isLoading` gate.

## Components

### `components/layout/RequestResponseWorkbench.tsx` (new)

Extracts the request panel + response panel from `WorkspaceView` — today's `mainArea`
`TwoPanel`, including both tab bars (`REQUEST_TABS`, `RESPONSE_TABS`) and the viewers. It
reads `requestStore` / `responseStore` / `sessionStore` internally (matching the existing
pattern where `ParamsTab`, `HeadersTab`, `ScriptOutput`, etc. read the stores directly),
derives `isStreaming` from `responseStore.streaming`, and exposes exactly two props:

```ts
interface RequestResponseWorkbenchProps {
  onSend: () => void;
  onCancel: () => void;
}
```

- `WorkspaceView` renders `<Sidebar/>` + `<RequestResponseWorkbench onSend={handleSend} onCancel={cancel}/>`
  and keeps its Cmd+S save handler. The request/response tab definitions and the `mainArea`
  JSX move out of `WorkspaceView` into the workbench.
- `TutorialView` renders the coach rail + `<RequestResponseWorkbench onSend={…} onCancel={…}/>`.

### `AppBar.tsx` (modified)

- Add **Workspace / Tutorial segmented tabs** next to the logo (left), replacing the current
  right-side "Tutorial" button. They drive `viewStore.setView`. Active tab uses the
  established pill idiom (`bg-primary/10 text-primary`); inactive uses
  `text-muted-foreground hover:text-foreground`.
- `WorkspaceSwitcher` stays (visible in both modes for layout stability; it has no effect
  during the tutorial). `ThemeToggle` stays in the right slot.

### `TutorialView.tsx` (slimmed)

- **Removed:** its own `<nav>`, the `ThemeToggle` import, the hardcoded `STEPS` array, and
  the `displayMethod`/`displayUrl`/bespoke request card + response block.
- **Body:** coach rail (`w-72` left column — Progress step list with ✓/▶/○, scrollable
  Instructions, Back/Next) + `RequestResponseWorkbench`.
- Step titles + instructions come from `useTutorialSteps()`. `currentStep` and
  `completedSteps` remain local React state.
- **Store isolation:** on mount, snapshot `requestStore`, `responseStore`, and
  `sessionStore` (via `useX.getState()`); on unmount, restore them (via `useX.setState(...)`).
  This guarantees entering/leaving the tutorial never disturbs the user's in-progress
  workspace request/response/session state.
- **Per-step seeding** (on `currentStep` change):
  - `requestStore.load(syntheticDetail)` — a `RequestDetail` built from the step (virtual
    path) so the real `UrlBar` + all request tabs render genuine content (e.g. the
    `q=sunflowers` param in Params, the pre/post scripts in Scripts). `load()` does not
    touch `selectedPath`.
  - `responseStore.reset()`.
  - `sessionStore.setVariables(step.variable_overrides)` — so `{{base_url}}` renders as a
    *known* variable chip in `UrlBar` for the env-var step.
- **No-request steps** (`method` null, e.g. Welcome): the workbench area shows a centered
  placeholder ("This step has no request — read the instructions and click Next"); the Send
  action is unreachable.

## Data flow (frontend)

### `api/tutorial.ts` (new)

- `useTutorialSteps()` — React Query fetching `GET /api/tutorial/steps`, `staleTime: Infinity`.
- `useTutorialSend()` — returns `{ send(stepIndex), cancel }`, mirroring `useSend`. It reuses
  an **exported `parseSSE`** helper from `useSend.ts`, POSTs to
  `/api/tutorial/steps/{stepIndex}/send` (no body), and writes results into `responseStore`
  via the same setters (`setStatus`/`setHeaders`/`setBody`/`setDone`/`setError`). `history_id`
  is always null, so no history-query invalidation.

`useSend.ts` is refactored to export `parseSSE`; its own behavior is unchanged.

### Send path

`TutorialView` passes `onSend={() => tutorialSend.send(currentStep)}` and
`onCancel={tutorialSend.cancel}` to the workbench. The real Send button in `UrlBar` therefore
drives the tutorial endpoint, and the real response pane renders the result from
`responseStore`.

## Backend / API

### `GET /api/tutorial/steps` (new)

Returns the existing `STEPS: list[TutorialStep]` from `drummer/api/routes/tutorial.py`
(`title`, `instructions`, `method`, `url`, `params`, `headers`, `pre_script`, `post_script`,
`body`, `variable_overrides`). The handler delegates to the module-level `STEPS` constant —
no business logic in the handler, typed Pydantic response (a `list[TutorialStep]`). This
becomes the single source of truth, deleting the duplicated `STEPS` array in
`TutorialView.tsx`.

`POST /api/tutorial/steps/{step_index}/send` is unchanged.

## Testing

**Backend (pytest)**
- Integration test for `GET /api/tutorial/steps`: returns the 7 steps with expected fields
  (titles, methods, the `q=sunflowers` param, the pre/post scripts, the `base_url` override).
- Existing send-endpoint tests unchanged.

**Frontend (vitest)**
- `AppBar` test: renders Workspace/Tutorial tabs; clicking Tutorial sets `view`; active tab
  styling; exactly one `ThemeToggle` in the bar.
- Update `TutorialView.test.tsx`: no own nav/`ThemeToggle`; a request step preloads into the
  real `UrlBar` (method + url visible) and request tabs; clicking Send triggers the tutorial
  send and the response renders via `responseStore`; Back/Next and progress markers work;
  no-request step shows the placeholder.
- Optionally a focused `RequestResponseWorkbench` test, or coverage via the WorkspaceView /
  TutorialView tests.

**Gate:** `make check` (ruff + pyright + pytest + vitest) stays green. No suppression comments.

## Docs / roadmap updates

- `ROADMAP.md` Phase 13 line → *"Tutorial drives the real request/response panes; unified
  Workspace/Tutorial tabs in the AppBar."* (drops "project pane steps"); mark ✅ Done at the
  milestone.
- `CLAUDE.md` → "Current phase: **13 — Tutorial cohesion**".

## Open considerations (resolve during planning, not blocking)

- Exact visual treatment of the AppBar tabs (pill vs. underline) — pill per the design;
  finalize against the Phase 12 idioms during implementation.
- Whether to fully replace `TutorialView.test.tsx` or extend it, given the structural change.
