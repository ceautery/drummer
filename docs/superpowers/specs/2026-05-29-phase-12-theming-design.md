# Phase 12 — Theming (Dark / Light / System)

**Status:** Approved design — ready for implementation plan
**Date:** 2026-05-29
**Author:** brainstormed with Claude

## Context

Drummer's UI is split: the workspace app (`AppBar`, `WorkspaceView`, request/response
components) is hardcoded-light, while `TutorialView` is hardcoded-dark and patches a white
card around the *shared* response components (`ResponseMeta` / `BodyViewer` / `ScriptOutput`)
so they still render. A token foundation already exists — `index.css` defines a full light
(`:root`) + dark (`.dark`) OKLCH palette and a class-based dark variant
(`@custom-variant dark (&:is(.dark *))`) — and the `components/ui/*` primitives already use
those tokens. This phase wires a user-facing **light / dark / system** toggle, persists the
choice, and converts the remaining hardcoded colors so one tokenized theme drives both the
app and the tutorial.

This is the second of the new arc (11 Workspaces → **12 Theming** → 13 Tutorial cohesion →
14 Wikidata GraphQL). It builds on Phase 11's `AppBar` (which deliberately left a right-side
slot for this toggle) and `config.yaml` (whose writer already preserves extra keys).

## Goals

- A **light / dark / system-auto** theme toggle reachable from the AppBar **and** the tutorial.
- Theme applies across the **whole app and the tutorial** — no view stays hardcoded.
- Preference **persisted in `~/.drummer/config.yaml`** so it survives restarts.
- `system` mode follows the OS preference and updates **live** when the OS theme changes.
- No white flash on first paint.

## Non-goals

- Per-workspace themes — theme is a single global preference.
- New palette beyond the existing token set + a brand accent (no multi-theme / custom-color
  picker).
- Merging the tutorial nav into the AppBar tabs — that is Phase 13. For now the toggle is
  duplicated into the tutorial's own nav (accepted as slightly throwaway).
- Theming the marketing/docs site (`docs/site`), which is outside the React app.

## Key decisions

| Decision | Choice |
|---|---|
| Modes | **light / dark / system**; default **system** on fresh install |
| Persistence | **`~/.drummer/config.yaml`** (`theme:` key), server-side |
| Toggle UI | **Icon button → dropdown menu** (base-ui Select, like `WorkspaceSwitcher`), checkmark on active mode |
| Toggle placement | AppBar right slot **and** the tutorial's own nav (shared component) |
| Palette identity | **Drummer purple brand accent** — `--primary` resolves to purple in both themes |
| CodeMirror light theme | CodeMirror's built-in default light (no new dependency); `oneDark` in dark |

## Palette

- `--primary` / `--primary-foreground` change to a purple brand accent (≈ `#7c3aed`,
  expressed in OKLCH) in both `:root` and `.dark`, with white foreground. This folds the
  existing ad-hoc `purple-600` accent usage into the token system: primary buttons (Send),
  active tab underline, and focus rings pick it up.
- Semantic colors are **preserved, not flattened**: status green/red (`StatusBadge`,
  `ResponseMeta`), and the variable chips (known = purple, unknown = amber). Where these are
  hardcoded for light, add `dark:` variants / dark token overrides so they read correctly in
  both themes.

## Backend / core

### `core/storage/workspaces.py`

This module already owns `config.yaml` (via `get_active` / `set_active`). Extend it:

- Add `ThemePref = Literal["light", "dark", "system"]`.
- `get_theme() -> ThemePref` — read `config.yaml`; default `"system"` if absent or invalid.
- `set_theme(pref: ThemePref) -> None` — write `theme` key, preserving all other keys.
- Refactor the inline read-modify-write currently duplicated in `get_active` / `set_active`
  into shared `_read_config() -> dict` / `_write_config(dict) -> None` helpers, and route
  the new theme functions through them. This is a targeted dedupe in code being touched —
  key-preservation is already covered by an existing config test.

### `api/routes/settings.py` (new)

Thin router, no business logic in handlers (per CLAUDE.md) — delegates to core.

| Method & path | Purpose | Body / Returns |
|---|---|---|
| `GET /api/settings` | read settings | → `Settings` |
| `PUT /api/settings` | update settings | body `Settings` → updated `Settings` |

```python
class Settings(BaseModel):
    theme: ThemePref  # "light" | "dark" | "system"
```

No untyped dicts in responses. Register the router in the app the same way as
`workspaces` / `project`.

## Frontend

### Token & CSS work (`index.css`)

- Change `--primary` / `--primary-foreground` to the purple accent in **both** `:root` and
  `.dark`.
- Add `.dark` overrides for the hardcoded CodeMirror highlight colors (`.cm-var-known`,
  `.cm-var-unknown`) so the purple/amber highlights read correctly on a dark editor.
- Add a `@media (prefers-color-scheme: dark)` fallback that applies the dark token values
  when no explicit `.light` / `.dark` class is present yet, so the initial loading screen is
  system-appropriate before JS runs.

### Hardcoded-color conversion

Convert the ~135 hardcoded Tailwind color utilities across ~24 files to tokens. Representative
mappings: `bg-white` → `bg-background` / `bg-card`; `text-gray-500` → `text-muted-foreground`;
`text-gray-900` → `text-foreground`; `border-gray-200` → `border-border`; `bg-blue-600`
(primary actions) → `bg-primary`. Densest files (by current count): `TutorialView` (22 — also
**drop the white response-card wrapper** so the shared components theme themselves),
`SchemaExplorer` (15), `TreeNode` (12), `UrlBar` (11), `CookiesTab`, `AuthTab`, `ScriptTab`,
`HistoryDrawer`, `ScriptOutput`, `ResponseMeta`, `RawViewer`, `WorkspaceView`, `Sidebar`,
`AppBar`, and the remaining shared/request/response components. Semantic green/red/purple are
re-expressed as intentional tokens / `dark:` variants, **not** collapsed to grayscale.

### CodeMirror theming

`ScriptTab` currently hardcodes `oneDark`; `UrlBar` uses a custom `EditorView.theme`. Add a
`useEditorTheme()` hook (in `lib/`) returning the correct editor theme extension for the
active resolved mode (CodeMirror default light in light mode, `oneDark` in dark). Apply it via
a CodeMirror `Compartment` so the theme swaps live on toggle without remounting the editor.

### Theme state & application

- **`store/themeStore.ts`** (zustand): holds `theme: ThemePref` and a computed
  `resolved: "light" | "dark"` (resolving `system` via `matchMedia`).
- **`api/settings.ts`**: `useSettings` query + `useSetTheme` mutation (`PUT /api/settings`,
  optimistic update of the store).
- **`useApplyTheme()`** effect at the app root: toggles the `.dark` class on
  `document.documentElement` from `resolved`; when `theme === "system"`, subscribes to
  `matchMedia('(prefers-color-scheme: dark)')` and updates `resolved` live; unsubscribes on
  change/unmount.
- **First-paint flash**: theme is fetched as part of the initial load gate alongside
  `useProject`; the existing "Loading…" screen stays up until theme is known, so the real
  chrome only renders once the `.dark` class is correct. Combined with the
  `prefers-color-scheme` CSS fallback, there is no white flash.

### Toggle component

`components/layout/ThemeToggle.tsx` — a shared component built on `ui/select.tsx`: an icon
button (current mode's icon) that opens a menu of Light / Dark / System with a checkmark on
the active mode; selecting fires `useSetTheme`. Rendered in both `AppBar` (right slot,
alongside the Tutorial button) and `TutorialView`'s nav bar.

## Testing

**Backend**
- Unit (`DRUMMER_HOME` → tmp dir): `get_theme` default (`system`), `set_theme` round-trip,
  invalid value falls back to default, and `set_theme` preserves `active_workspace`
  (and vice versa) — extend the existing config key-preservation test.
- Integration: `GET /api/settings`, `PUT /api/settings` round-trip + validation of bad theme
  values.

**Frontend (vitest)**
- `themeStore`: `system` resolves to light/dark from the media query; explicit modes resolve
  to themselves.
- `ThemeToggle`: renders three options with the active one marked; selecting an option fires
  the mutation and results in the `.dark` class toggling.
- `TutorialView`: renders its toggle and honors the `.dark` class (no longer forced dark).

**Gate:** `make check` (ruff + pyright + pytest tests/unit tests/integration) stays green.
No suppression comments.

## Docs / project management

- Mark Phase 12 **in progress** in `ROADMAP.md`; set "Current phase: 12 — Theming" in
  `CLAUDE.md`.
- Add a short theming note to `README.md` (toggle, modes, persisted in `~/.drummer/config.yaml`).
- Commit to `main` and push at the milestone (standing solo-team preference).

## Open considerations (resolve during planning, not blocking)

- Exact OKLCH values for the purple `--primary` in light vs. dark (ensure AA contrast against
  `--primary-foreground` white in both).
- Whether `useEditorTheme` lives as a hook or a small module returning a memoized Compartment
  effect — pick during implementation.
- Whether `GET /api/settings` is folded into the existing initial-load query batch or fetched
  by its own query that gates render — either is fine as long as no flash results.
