# Phase 16 — Environment & Variable Editor — Design

**Date:** 2026-05-30
**Status:** Approved (brainstorming)
**Arc:** Post-1.0 hardening (`docs/superpowers/specs/2026-05-29-post-1.0-hardening-arc-design.md`)

## Context

Variables (e.g. `{{base_url}}`) are defined only in per-environment YAML files
(`.drummer/environments/<name>.yaml`: a `name` plus a `variables` map; resolved by
`drummer/core/variables.py`). Today the UI exposes environments through a **read-only
selector** in the sidebar — there is no way to view or edit variables, and no way to add
or remove environments. Setting `{{base_url}}` currently requires hand-editing YAML.

This phase makes environments and their variables fully manageable from the app.

### What already exists (so this is smaller than it looks)
- **Backend:** `GET /api/environments` (list summaries), `GET /api/environments/{name}`
  (detail), `PUT /api/environments/{name}` (update — 404s if the file is absent). Core
  helpers `Environment`, `load_environment`, `save_environment`, `list_environments` in
  `drummer/core/storage/project.py`.
- **Frontend:** `useEnvironments` (list) is wired into the sidebar selector;
  `useEnvironment` (detail) and `useSaveEnvironment` (PUT) **exist but are unused**; a
  reusable `KeyValueTable` component (add/edit/remove key→value rows) exists.
- **UI toolkit:** components are built on **Base UI** (`@base-ui/react`, already a
  dependency) in a shadcn-style wrapper pattern (see `components/ui/select.tsx`).

### Gaps this phase closes
1. Backend **create (POST)** and **delete (DELETE)** for environments.
2. A **variable editor UI** (modal) and the create/delete controls.
3. Wiring it into the sidebar and the active-environment state.

## Scope (decided during brainstorming)
- **In:** edit a chosen environment's variables; create a new environment; delete one.
- **Out (deferred):** environment **rename** — renaming the YAML file is the same
  "move file" primitive deferred for request rename, and additionally requires fixing up
  `project.yaml`'s `default_environment` and the active selection. Also out (YAGNI):
  shared/global variables, secret masking, import/export.

## Architecture

No layer-boundary changes (additive within `core` / `api` / `frontend`) → no ADR. File
I/O stays in `drummer/core/storage/`. `make check` green per commit; because `make check`
does **not** run the frontend vitest suite, run `npm run test` (vitest run) explicitly
before any frontend commit.

### Backend

`drummer/core/storage/project.py`
- Add **`delete_environment(name: str, project_dir: Path) -> None`** — deletes
  `.drummer/environments/<name>.yaml`. (Create needs no new helper: `save_environment`
  already writes the file.)

`drummer/api/routes/environments.py`
- **`POST /api/environments`** — body `{ name: str, variables?: dict[str,str] }`, status
  201, returns `EnvironmentDetail`.
  - 409 if the environment already exists.
  - 400 if the name is empty or not filename-safe. Validation: reject blank/whitespace and
    any name whose resolved path escapes the environments dir (reuse the existing
    `_safe_env_path` traversal guard; add an explicit blank/`/` check so the message is
    clear).
- **`DELETE /api/environments/{name}`** — status 204; 404 if the file is absent. Uses
  `_safe_env_path`.
- PUT (update) is unchanged.

### Frontend

`frontend/src/api/environments.ts`
- Add **`useCreateEnvironment`** (POST `{name, variables}`) and **`useDeleteEnvironment`**
  (DELETE by name). Both `invalidateQueries(["environments"])` on success.
  `useEnvironment` and `useSaveEnvironment` already exist and will now be consumed.

`frontend/src/components/ui/dialog.tsx` (new)
- A thin shadcn-style wrapper over `@base-ui/react/dialog`, matching the conventions in
  `components/ui/select.tsx` (Root/Trigger/Portal/Backdrop/Popup/Title/Close as needed).
  Reusable beyond this phase.

`frontend/src/components/layout/EnvironmentManager.tsx` (new)
- The "Manage Environments" modal. Contains:
  - An environment **picker** (reuse `Select`) for *which environment to edit*, a
    **+ New** action, and a **🗑 Delete** button.
  - Loads the picked environment via `useEnvironment`; holds a **local draft** of its
    variables; renders `KeyValueTable` for add/edit/remove.
  - **Save** → `useSaveEnvironment`. **+ New** → prompt for a name →
    `useCreateEnvironment` → select the new env. **Delete** → `window.confirm` →
    `useDeleteEnvironment`.
- The modal's picker (which env to *edit*) is intentionally distinct from the sidebar
  selector (which env is *active* for sending).

`frontend/src/components/layout/Sidebar.tsx`
- Add a **gear/Manage button** next to the environment selector that opens the modal. The
  Manage affordance renders even when the environment list is empty, so the modal's
  **+ New** can bootstrap the first environment. (Today the sidebar hides the entire env
  block at zero environments.)

`frontend/src/store/sessionStore.ts`
- No shape change. After a delete that removes the **active** environment, the app resets
  `activeEnvironment` to the project's `default_environment` if it still exists, else the
  first remaining environment, else `"local"`.

## State & edge cases
- **Active-environment fallback** on delete: as above (default → first remaining →
  `"local"`).
- **Unsaved edits guard:** if the variable draft is dirty and the user switches the picked
  environment (or triggers create/delete), confirm-discard — mirrors the request-pane
  dirty guard already in the app.
- **First-env case:** projects are created with a `local` environment, so the list is
  normally non-empty; the always-visible Manage affordance covers the empty case anyway.
- **Variable model unchanged:** per-environment key→value strings only; same resolution
  the engine already performs. No precedence changes.

## Error handling
- **Duplicate name** on create → 409 → inline error in the modal (e.g. "An environment
  named 'x' already exists"); the modal stays open.
- **Empty/invalid name** → rejected client-side and 400 server-side.
- **Delete** → `window.confirm` gate first; a 404 should not occur from the UI.

## Testing
- **Backend:**
  - Integration: POST create → 201 and the file exists; duplicate name → 409; invalid
    name (blank, `..`, `/`) → 400. DELETE → 204 and the file is gone; missing → 404.
  - Unit: `delete_environment` unlinks the file. Contract: the **route** checks existence
    first and returns 404 if absent; the core helper simply unlinks (it assumes the caller
    has confirmed the file exists).
- **Frontend:**
  - Hook tests for `useCreateEnvironment` / `useDeleteEnvironment` via `renderHook` +
    mocked `apiFetch`, using the `tsc -b`-safe accessor pattern established in Phase 15
    (`vi.mocked(apiFetch).mock.calls[0]?.[1]` / `toHaveBeenCalledWith`, never tuple
    destructure of `mock.calls[0]`).
  - Component test for `EnvironmentManager` (env api module mocked): renders a selected
    env's variables; add/remove a row updates the draft; Save calls `useSaveEnvironment`
    with the edited variables; the create flow calls `useCreateEnvironment`; the delete
    flow (confirm) calls `useDeleteEnvironment`.
  - No dedicated test for the `dialog.tsx` primitive.

## Out of scope
- Environment rename / move.
- Shared/global variables, secret masking, import/export.
