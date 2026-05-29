# Phase 11 — Workspaces (Projects & CLI Pivot)

**Status:** Approved design — ready for implementation plan
**Date:** 2026-05-29
**Author:** brainstormed with Claude

## Context

Drummer currently binds a single project at server startup (`create_app(project_dir=...)`)
and asks the user to either pass `--project /path` or type a folder path into a Welcome
screen. This phase pivots to a **workspaces** model: a zero-config catchall space, central
storage under `~/.drummer/`, and the ability to switch workspaces during a session via a
dropdown in a new top app bar.

This is the first of four new phases (11 Workspaces → 12 Theming → 13 Tutorial cohesion →
14 Wikidata GraphQL). It is built first because it is the largest structural pivot and
later phases (the tutorial's project-pane step, the top-bar tabs and theme toggle) build on
the app bar and workspace model introduced here.

## Goals

- `drummer` with no subcommand launches the server.
- A default **Scratch** workspace so the user can add requests immediately with no setup.
- Workspaces stored in a common place (`~/.drummer/`), not arbitrary user folders — while
  still supporting registered **external** folders so the existing git-friendly,
  "point Drummer at my repo" workflow is preserved.
- A **workspace switcher** in a new persistent top app bar that lets the user cycle between
  workspaces mid-session.

## Non-goals

- Theming (Phase 12), Workspace/Tutorial tabs and theme toggle in the app bar (Phases 12–13).
- Multi-user / concurrent-session handling. Drummer remains a single-user local tool; the
  active workspace is per-server state.
- Reworking the request/environment/cookie storage *inside* a workspace — the per-workspace
  `.drummer/` layout from earlier phases is unchanged.

## Key decisions

| Decision | Choice |
|---|---|
| Storage relationship to user folders | **Central default + register external folders** |
| Storage root | **`~/.drummer/`** (same path macOS + Linux) |
| Catchall workspace | **"Scratch"** — auto-created, special: non-deletable, non-renamable, pinned top of dropdown |
| Switcher placement | **Top app bar, top-left** next to the logo (placement A) |

## Storage layout

```
~/.drummer/
├── config.yaml          # global config: active_workspace (theme added in P12)
├── registry.yaml        # registered EXTERNAL folder paths only
└── projects/            # central workspaces
    ├── scratch/         # the catchall — auto-created, special
    │   └── .drummer/
    │       ├── project.yaml
    │       └── environments/local.yaml
    └── my-api/
        └── .drummer/...
```

- **Central workspaces** are discovered by scanning `projects/*/.drummer/project.yaml`.
  They need no registry entry.
- **External workspaces** are absolute paths listed in `registry.yaml`. The repo stays
  wherever it lives on disk.
- The dropdown merges central + external; external entries carry an "external" badge and a
  truncated path.
- `scratch/` is bootstrapped on first run if absent. It cannot be deleted or renamed.
- Cookies / OAuth state introduced in Phase 9 remain inside each workspace's `.drummer/` —
  unchanged.

### `config.yaml`

```yaml
active_workspace: scratch   # central slug, or an external path
```

`active_workspace` persists across restarts so reopening resumes the last workspace.
Defaults to `scratch` on first run. If it points at a workspace that no longer exists,
fall back to `scratch`.

### `registry.yaml`

```yaml
external:
  - /Users/me/code/acme-api
  - /Users/me/work/other-repo
```

## CLI changes (`drummer/cli.py`)

- `drummer` (no subcommand) → **launches the server**. The previous behavior (printing help
  when no subcommand) is replaced. `--port`, `--host`, and `--project PATH` move onto the
  top-level callback. `--attribution` / `--version` still short-circuit and exit.
- `drummer serve` → kept as a **hidden alias** that delegates to the same launch path, for
  back-compat.
- `drummer --project /path` → registers the external folder (if not already registered) and
  opens it as the active workspace. If the folder lacks `.drummer/project.yaml`, Drummer
  initializes a minimal one (reusing `create_project`).
- `drummer new NAME` → creates a **central** workspace at `~/.drummer/projects/<slug>` and
  prints its path. (De-stubbed.) `<slug>` is a slugified form of `NAME`.
- `drummer export NAME` → **deferred to a later phase**; leave the existing stub. (Avoids
  bloating Phase 11; not required for the workspace pivot.)
- `drummer mcp` → unchanged.

When launching, the startup banner reports the active workspace name.

## Backend / core

### `drummer/core/storage/workspaces.py` (new)

Pure-Python module, independently testable, no FastAPI imports. Responsibilities:

- `root() -> Path` — resolve `~/.drummer` (overridable via `DRUMMER_HOME` env var for tests).
- `ensure_scratch() -> None` — create the Scratch workspace if missing.
- `list_workspaces() -> list[WorkspaceInfo]` — scan `projects/*` + read `registry.yaml`;
  Scratch first, then other central (sorted), then external (sorted).
- `register_external(path: Path) -> WorkspaceInfo` — validate/initialize, append to registry.
- `create_workspace(name: str) -> WorkspaceInfo` — slugify, create central dir via
  `create_project`.
- `resolve_workspace(id: str) -> Path` — map a workspace id (central slug or external path)
  to its project directory.
- `get_active() / set_active(id)` — read/write `config.yaml`; validate existence with
  fallback to `scratch`.

### Pydantic models

```python
class WorkspaceInfo(BaseModel):
    id: str            # central slug, or absolute path for external
    name: str          # display name (project.yaml name, or folder name)
    kind: Literal["central", "external"]
    path: str          # absolute project dir
    is_scratch: bool
```

No untyped dicts in responses (per CLAUDE.md).

### Active workspace as server state

Today `create_app(project_dir=...)` freezes the project. Generalize to an app-level mutable
"active workspace" holder. On startup: `ensure_scratch()`, then load `get_active()` (or the
`--project` override). Routes that currently read the single project read the active
workspace's dir instead. This mirrors the existing `set-project` route precedent.

## API (`drummer/api/routes/`)

Replace/extend the current project route with a `workspaces` router. No business logic in
handlers — all calls delegate to `core/storage/workspaces.py`.

| Method & path | Purpose | Returns |
|---|---|---|
| `GET /api/workspaces` | list all + which is active | `{ workspaces: WorkspaceInfo[], active: str }` |
| `POST /api/workspaces/active` | switch active workspace | active `WorkspaceInfo` |
| `POST /api/workspaces` | create central workspace | new `WorkspaceInfo` |
| `POST /api/workspaces/register` | register an external folder | new `WorkspaceInfo` |

The existing project-detail endpoint(s) continue to serve the *active* workspace so the
request tree / environments / history routes need no change beyond reading active state.

## Frontend

### Top app bar — `components/layout/AppBar.tsx` (new)

Persistent bar above the sidebar + panels, rendered by the app shell. Phase 11 contents:
`🥁 Drummer` logo (left) + **workspace switcher**. Right side intentionally left empty —
reserved for Phase 12's theme toggle and Phase 13's Workspace/Tutorial tabs. The "Try the
tutorial" entry point (previously on WelcomeView) moves here so it is not lost.

### Workspace switcher — `components/layout/WorkspaceSwitcher.tsx` (new)

Built on the existing `ui/select.tsx` primitive. Dropdown order:

1. **⌂ Scratch** — pinned, checkmark when active
2. divider
3. other central workspaces
4. external workspaces — "external" badge + truncated path
5. divider
6. **+ New workspace…** — prompts for a name → `POST /api/workspaces` → switch to it
7. **⊕ Add existing folder…** — prompts for a path → `POST /api/workspaces/register` → switch

Inline prompt/input for this phase; no heavy modal.

### Switching behavior

- Selecting a workspace → `POST /api/workspaces/active`. On success, invalidate the React
  Query caches for requests / environments / history so the tree and session reload.
- If the current request has unsaved edits, reuse the existing confirm-discard guard
  (`isDirty()` in `WorkspaceView`) before switching.

### State / data layer

- New `api/workspaces.ts` — query (`useWorkspaces`) + mutations (`useSwitchWorkspace`,
  `useCreateWorkspace`, `useRegisterWorkspace`).
- Active workspace + list held in `projectStore` (extended) or a small `workspaceStore`.

### Welcome screen removed

`WelcomeView` (path-input card) is **deleted**. The app always boots into a real workspace
(Scratch by default). `App.tsx` simplifies to: load active workspace → render `AppBar` +
`WorkspaceView`. "Open a project" is now the switcher's "Add existing folder…".

## Testing

**Backend**
- Unit tests for `workspaces.py` using `DRUMMER_HOME` pointed at a tmp dir: scratch
  bootstrap, central scan ordering, external registration + initialization, active
  persistence + fallback, slugify behavior.
- Integration tests for the four routes.

**Frontend**
- `WorkspaceSwitcher` test: renders Scratch pinned, switch fires the mutation, external
  badge shown.
- `App` test: boots into Scratch (replaces the removed WelcomeView test).

**Gate:** `make check` (ruff + pyright + pytest) stays green. No suppression comments.

## Roadmap / docs updates

- Add Phases 11–14 to `ROADMAP.md` (high level).
- Set "Current phase: 11 — Workspaces" in `CLAUDE.md`.
- Update `README.md` Quick start + project sections: `drummer` to launch, Scratch default,
  `~/.drummer/` storage, registering external folders.

## Open considerations (resolve during planning, not blocking)

- Slug collision handling for `drummer new` / external names (e.g., append `-2`).
- Whether "Add existing folder…" surfaces a server-side path picker or stays a typed path
  (typed path for this phase, matching the old WelcomeView affordance).
