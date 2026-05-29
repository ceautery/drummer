# Phase 12 — Theming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a light / dark / system-auto theme toggle that applies across the whole app and the tutorial, persisted server-side in `~/.drummer/config.yaml`.

**Architecture:** A `theme` key in `config.yaml` is the source of truth, read/written through `core/storage/workspaces.py` and exposed via a new `/api/settings` router. The frontend hydrates a zustand `themeStore` from `GET /api/settings`, toggles the `.dark` class on `<html>` (Tailwind v4's class-based dark variant already wired in `index.css`), and persists changes via `PUT /api/settings`. The existing hardcoded-color components are converted to the existing design tokens; `--primary` is repointed to a Drummer-purple accent in both themes; the four CodeMirror editors follow the theme via a reconfigurable Compartment.

**Tech Stack:** FastAPI + Pydantic (backend), pytest/httpx (tests), React 19 + zustand + TanStack Query + Tailwind v4 + base-ui Select + CodeMirror 6 (frontend), vitest + Testing Library (frontend tests).

---

## File Structure

**Backend**
- Modify `drummer/core/storage/workspaces.py` — add `ThemePref`, `_read_config`/`_write_config` helpers, `get_theme`/`set_theme`; route `get_active`/`set_active` through the helpers.
- Create `drummer/api/routes/settings.py` — `Settings` model + `GET`/`PUT /api/settings`.
- Modify `drummer/api/app.py` — register the settings router.
- Modify `tests/unit/test_workspaces.py` — theme unit tests.
- Create `tests/integration/test_settings_routes.py` — route tests.

**Frontend — foundation**
- Modify `frontend/src/types.ts` — `ThemePref`, `Settings`.
- Create `frontend/src/api/settings.ts` — `useSettings`, `useSetTheme`.
- Create `frontend/src/store/themeStore.ts` — theme pref + system-dark state + resolved selector.
- Create `frontend/src/store/themeStore.test.ts` — resolution tests.
- Create `frontend/src/lib/useApplyTheme.ts` — applies `.dark` class + matchMedia subscription.
- Create `frontend/src/lib/editorTheme.ts` — `editorThemeExtension(resolved)`.
- Create `frontend/src/components/layout/ThemeToggle.tsx` — shared toggle (base-ui Select).
- Create `frontend/src/components/layout/ThemeToggle.test.tsx`.
- Modify `frontend/index.html` — first-paint system-match bootstrap script.
- Modify `frontend/src/App.tsx` — settings load gate + `useApplyTheme`.
- Modify `frontend/src/index.css` — purple `--primary`, dark CodeMirror highlight overrides.

**Frontend — tokenize hardcoded colors**
- Modify layout/request/response/tree/shared components + `TutorialView` (enumerated in Tasks 8–11).
- Modify the four CodeMirror components (`ScriptTab`, `UrlBar`, `GraphQLTab`, `BodyTab`) for theme-following editors (Task 7).

**Docs**
- Modify `ROADMAP.md`, `CLAUDE.md`, `README.md` (Task 12).

---

## Task 1: Core — config helpers + theme get/set

**Files:**
- Modify: `drummer/core/storage/workspaces.py`
- Test: `tests/unit/test_workspaces.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_workspaces.py` (the `drummer_home` fixture and `import yaml`/`ws` already exist):

```python
def test_get_theme_defaults_to_system(drummer_home: Path) -> None:
    assert ws.get_theme() == "system"


def test_set_theme_round_trips(drummer_home: Path) -> None:
    ws.set_theme("dark")
    assert ws.get_theme() == "dark"


def test_get_theme_falls_back_on_invalid_value(drummer_home: Path) -> None:
    config = drummer_home / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(yaml.dump({"theme": "neon"}))
    assert ws.get_theme() == "system"


def test_set_theme_preserves_active_workspace(drummer_home: Path) -> None:
    config = drummer_home / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(yaml.dump({"active_workspace": "scratch"}))
    ws.set_theme("light")
    data = yaml.safe_load(config.read_text())
    assert data["active_workspace"] == "scratch"
    assert data["theme"] == "light"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/unit/test_workspaces.py -k theme -v`
Expected: FAIL — `AttributeError: module 'drummer.core.storage.workspaces' has no attribute 'get_theme'`.

- [ ] **Step 3: Implement helpers + theme functions**

In `drummer/core/storage/workspaces.py`, add `ThemePref` near the top (after the existing `Literal` import is already present):

```python
ThemePref = Literal["light", "dark", "system"]
_VALID_THEMES: set[str] = {"light", "dark", "system"}
```

Add config read/write helpers (place them just above `get_active`):

```python
def _read_config() -> dict[str, object]:
    path = _config_path()
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_config(data: dict[str, object]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
```

Refactor `get_active` / `set_active` to use them:

```python
def get_active() -> str:
    data = _read_config()
    active = data.get("active_workspace")
    if isinstance(active, str) and _workspace_exists(active):
        return active
    return "scratch"


def set_active(workspace_id: str) -> None:
    data = _read_config()
    data["active_workspace"] = workspace_id
    _write_config(data)
```

Add the theme functions (place after `set_active`):

```python
def get_theme() -> ThemePref:
    value = _read_config().get("theme")
    if isinstance(value, str) and value in _VALID_THEMES:
        return cast("ThemePref", value)
    return "system"


def set_theme(pref: ThemePref) -> None:
    data = _read_config()
    data["theme"] = pref
    _write_config(data)
```

(`cast` is already imported from `typing` in this module.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/unit/test_workspaces.py -v`
Expected: PASS — the new theme tests plus the existing `test_set_active_preserves_other_config_keys` all green.

- [ ] **Step 5: Commit**

```bash
git add drummer/core/storage/workspaces.py tests/unit/test_workspaces.py
git commit -m "feat(core): theme get/set in config.yaml + shared config read/write helpers"
```

---

## Task 2: API — settings router

**Files:**
- Create: `drummer/api/routes/settings.py`
- Modify: `drummer/api/app.py`
- Test: `tests/integration/test_settings_routes.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/integration/test_settings_routes.py` (mirror the style of `test_workspaces_routes.py`; the `client` fixture comes from `tests/integration/conftest.py`):

```python
from http import HTTPStatus

from httpx import AsyncClient


async def test_get_settings_defaults_to_system(client: AsyncClient) -> None:
    r = await client.get("/api/settings")
    assert r.status_code == HTTPStatus.OK
    assert r.json()["theme"] == "system"


async def test_put_settings_round_trips(client: AsyncClient) -> None:
    r = await client.put("/api/settings", json={"theme": "dark"})
    assert r.status_code == HTTPStatus.OK
    assert r.json()["theme"] == "dark"
    assert (await client.get("/api/settings")).json()["theme"] == "dark"


async def test_put_settings_rejects_invalid_theme(client: AsyncClient) -> None:
    r = await client.put("/api/settings", json={"theme": "neon"})
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
```

> Note: the integration `client` fixture in `tests/integration/conftest.py` builds the app with a `project_dir` under `tmp_path` but does **not** set `DRUMMER_HOME`, so `config.yaml` would resolve to the real `~/.drummer`. To keep the settings tests hermetic, add a `DRUMMER_HOME` monkeypatch fixture local to this file:

```python
import pytest


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRUMMER_HOME", str(tmp_path / "home"))
```

Place this fixture at the top of the test file (after imports), and add `import pytest` / the `tmp_path`, `monkeypatch` params.

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/integration/test_settings_routes.py -v`
Expected: FAIL — all 404 (route not registered yet).

- [ ] **Step 3: Create the router**

Create `drummer/api/routes/settings.py`:

```python
from pydantic import BaseModel

from fastapi import APIRouter

from drummer.core.storage import workspaces as ws

router = APIRouter()


class Settings(BaseModel):
    theme: ws.ThemePref


@router.get("/settings")
async def get_settings_route() -> Settings:
    return Settings(theme=ws.get_theme())


@router.put("/settings")
async def put_settings_route(body: Settings) -> Settings:
    ws.set_theme(body.theme)
    return Settings(theme=ws.get_theme())
```

- [ ] **Step 4: Register the router in `drummer/api/app.py`**

Add the import alongside the other route imports (e.g. near `from drummer.api.routes import workspaces as workspace_routes`):

```python
from drummer.api.routes import settings as settings_routes
```

Add the registration alongside the other `include_router` calls:

```python
app.include_router(settings_routes.router, prefix="/api")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv/bin/pytest tests/integration/test_settings_routes.py -v`
Expected: PASS (3 tests). The `422` is FastAPI/Pydantic rejecting the bad `Literal` value automatically.

- [ ] **Step 6: Commit**

```bash
git add drummer/api/routes/settings.py drummer/api/app.py tests/integration/test_settings_routes.py
git commit -m "feat(api): GET/PUT /api/settings for theme preference"
```

---

## Task 3: Frontend — types, settings API hooks, theme store

**Files:**
- Modify: `frontend/src/types.ts`
- Create: `frontend/src/api/settings.ts`
- Create: `frontend/src/store/themeStore.ts`
- Test: `frontend/src/store/themeStore.test.ts`

- [ ] **Step 1: Add types**

Append to `frontend/src/types.ts`:

```typescript
export type ThemePref = "light" | "dark" | "system";

export interface Settings {
  theme: ThemePref;
}
```

- [ ] **Step 2: Write the failing store test**

Create `frontend/src/store/themeStore.test.ts`:

```typescript
import { beforeEach, describe, expect, it } from "vitest";
import { resolveTheme, useThemeStore } from "./themeStore";

describe("themeStore", () => {
  beforeEach(() => {
    useThemeStore.setState({ theme: "system", systemDark: false });
  });

  it("resolves explicit modes to themselves", () => {
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });

  it("resolves system to the OS preference", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
  });

  it("setTheme updates the store", () => {
    useThemeStore.getState().setTheme("dark");
    expect(useThemeStore.getState().theme).toBe("dark");
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/store/themeStore.test.ts`
Expected: FAIL — cannot resolve `./themeStore`.

- [ ] **Step 4: Implement the store**

Create `frontend/src/store/themeStore.ts`:

```typescript
import { create } from "zustand";
import type { ThemePref } from "../types";

export type ResolvedTheme = "light" | "dark";

export function resolveTheme(theme: ThemePref, systemDark: boolean): ResolvedTheme {
  if (theme === "system") return systemDark ? "dark" : "light";
  return theme;
}

interface ThemeState {
  theme: ThemePref;
  systemDark: boolean;
  setTheme: (theme: ThemePref) => void;
  setSystemDark: (systemDark: boolean) => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: "system",
  systemDark: false,
  setTheme: (theme) => set({ theme }),
  setSystemDark: (systemDark) => set({ systemDark }),
}));

export function useResolvedTheme(): ResolvedTheme {
  const theme = useThemeStore((s) => s.theme);
  const systemDark = useThemeStore((s) => s.systemDark);
  return resolveTheme(theme, systemDark);
}
```

- [ ] **Step 5: Implement the settings API hooks**

Create `frontend/src/api/settings.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useThemeStore } from "../store/themeStore";
import type { Settings, ThemePref } from "../types";
import { apiFetch } from "./client";

export function useSettings() {
  return useQuery<Settings>({
    queryKey: ["settings"],
    queryFn: () => apiFetch<Settings>("/api/settings"),
  });
}

export function useSetTheme() {
  const qc = useQueryClient();
  const setTheme = useThemeStore((s) => s.setTheme);
  return useMutation<Settings, Error, ThemePref>({
    mutationFn: (theme) => {
      setTheme(theme); // optimistic: apply immediately
      return apiFetch<Settings>("/api/settings", {
        method: "PUT",
        body: JSON.stringify({ theme }),
      });
    },
    onSuccess: (data) => {
      setTheme(data.theme);
      void qc.invalidateQueries({ queryKey: ["settings"] });
    },
  });
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/store/themeStore.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/settings.ts frontend/src/store/themeStore.ts frontend/src/store/themeStore.test.ts
git commit -m "feat(frontend): theme store + settings API hooks"
```

---

## Task 4: Frontend — token palette (purple accent) + CSS + first-paint bootstrap

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/index.html`

- [ ] **Step 1: Repoint `--primary` to Drummer purple (light)**

In `frontend/src/index.css`, inside `:root { … }`, replace the two primary lines:

```css
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
```

with:

```css
  --primary: oklch(0.546 0.245 293);
  --primary-foreground: oklch(0.985 0 0);
```

- [ ] **Step 2: Repoint `--primary` to Drummer purple (dark)**

Inside `.dark { … }`, replace:

```css
  --primary: oklch(0.922 0 0);
  --primary-foreground: oklch(0.205 0 0);
```

with:

```css
  --primary: oklch(0.62 0.235 293);
  --primary-foreground: oklch(0.985 0 0);
```

- [ ] **Step 3: Add dark overrides for the CodeMirror variable highlights**

In `frontend/src/index.css`, immediately after the existing `.cm-var-unknown { … }` block, add:

```css
.dark .cm-var-known {
  background: rgba(196, 181, 253, 0.18);
  color: #c4b5fd;
}
.dark .cm-var-unknown {
  background: rgba(252, 211, 77, 0.18);
  color: #fcd34d;
}
```

- [ ] **Step 4: Add the first-paint system-match bootstrap to `frontend/index.html`**

In `frontend/index.html`, inside `<head>` (just before `</head>`), add:

```html
    <script>
      // First-paint: match the OS until the persisted theme loads (avoids flash).
      if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        document.documentElement.classList.add("dark");
      }
    </script>
```

- [ ] **Step 5: Verify the app still builds and lints**

Run: `cd frontend && npm run check`
Expected: PASS (biome + tsc, no errors).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/index.css frontend/index.html
git commit -m "feat(frontend): purple --primary accent, dark CodeMirror highlights, first-paint bootstrap"
```

---

## Task 5: Frontend — apply theme + App load gate

**Files:**
- Create: `frontend/src/lib/useApplyTheme.ts`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Implement the apply hook**

Create `frontend/src/lib/useApplyTheme.ts`:

```typescript
import { useEffect } from "react";
import { useResolvedTheme, useThemeStore } from "../store/themeStore";

/** Subscribes to the OS preference and reflects the resolved theme onto <html>. */
export function useApplyTheme(): void {
  const setSystemDark = useThemeStore((s) => s.setSystemDark);
  const resolved = useResolvedTheme();

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    setSystemDark(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setSystemDark(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [setSystemDark]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", resolved === "dark");
  }, [resolved]);
}
```

- [ ] **Step 2: Wire settings hydration + apply into `App.tsx`**

Replace the contents of `frontend/src/App.tsx` with:

```typescript
import { useEffect } from "react";
import { useProject } from "./api/projects";
import { useSettings } from "./api/settings";
import { AppBar } from "./components/layout/AppBar";
import { useApplyTheme } from "./lib/useApplyTheme";
import { useProjectStore } from "./store/projectStore";
import { useThemeStore } from "./store/themeStore";
import { useViewStore } from "./store/viewStore";
import { TutorialView } from "./views/TutorialView";
import { WorkspaceView } from "./views/WorkspaceView";

export default function App() {
  const view = useViewStore((s) => s.view);
  const { data: project, isLoading } = useProject();
  const { data: settings, isLoading: settingsLoading } = useSettings();
  const setProject = useProjectStore((s) => s.setProject);
  const setTheme = useThemeStore((s) => s.setTheme);

  useApplyTheme();

  useEffect(() => {
    if (project) setProject(project);
  }, [project, setProject]);

  useEffect(() => {
    if (settings) setTheme(settings.theme);
  }, [settings, setTheme]);

  if (settingsLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (view === "tutorial") return <TutorialView />;

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <AppBar />
      <div className="min-h-0 flex-1">
        <WorkspaceView />
      </div>
    </div>
  );
}
```

> Gating render on `settingsLoading` ensures the `.dark` class is correct (set by `useApplyTheme` once the store is hydrated) before the real chrome renders.

- [ ] **Step 3: Verify build/lint**

Run: `cd frontend && npm run check`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/useApplyTheme.ts frontend/src/App.tsx
git commit -m "feat(frontend): apply resolved theme to <html>, hydrate from settings with load gate"
```

---

## Task 6: Frontend — ThemeToggle component

**Files:**
- Create: `frontend/src/components/layout/ThemeToggle.tsx`
- Create: `frontend/src/components/layout/ThemeToggle.test.tsx`
- Modify: `frontend/src/components/layout/AppBar.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/layout/ThemeToggle.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useThemeStore } from "../../store/themeStore";
import { ThemeToggle } from "./ThemeToggle";

const mutate = vi.fn();
vi.mock("../../api/settings", () => ({
  useSetTheme: () => ({ mutate }),
}));

describe("ThemeToggle", () => {
  it("renders the trigger reflecting the active mode", () => {
    useThemeStore.setState({ theme: "dark", systemDark: false });
    render(<ThemeToggle />);
    expect(screen.getByLabelText(/theme/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/layout/ThemeToggle.test.tsx`
Expected: FAIL — cannot resolve `./ThemeToggle`.

- [ ] **Step 3: Implement the toggle**

Create `frontend/src/components/layout/ThemeToggle.tsx`. It mirrors the `WorkspaceSwitcher` Select usage:

```typescript
import { useMemo } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSetTheme } from "../../api/settings";
import { useThemeStore } from "../../store/themeStore";
import type { ThemePref } from "../../types";

const ICON: Record<ThemePref, string> = {
  light: "☀️",
  dark: "🌙",
  system: "🖥️",
};

const ORDER: ThemePref[] = ["light", "dark", "system"];

export function ThemeToggle() {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useSetTheme();

  const itemLabels = useMemo(
    () => ({
      light: <span>☀️</span>,
      dark: <span>🌙</span>,
      system: <span>🖥️</span>,
    }),
    [],
  );

  const handleChange = (value: string | null) => {
    if (value === null) return;
    setTheme.mutate(value as ThemePref);
  };

  return (
    <Select value={theme} onValueChange={handleChange} items={itemLabels}>
      <SelectTrigger size="sm" className="w-auto" aria-label="Theme">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {ORDER.map((mode) => (
          <SelectItem key={mode} value={mode}>
            <span className="flex items-center gap-2 capitalize">
              <span>{ICON[mode]}</span>
              {mode}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
```

> If the `items` prop on `Select` requires `Record<string, React.ReactNode>`, match the `WorkspaceSwitcher` typing (`useMemo<Record<string, React.ReactNode>>`). Verify against `frontend/src/components/ui/select.tsx` and align the generic exactly.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/layout/ThemeToggle.test.tsx`
Expected: PASS.

- [ ] **Step 5: Render the toggle in the AppBar**

Replace `frontend/src/components/layout/AppBar.tsx` with (also tokenizes its colors — see Task 8 mapping, done here since the file is small):

```typescript
import { useViewStore } from "../../store/viewStore";
import { ThemeToggle } from "./ThemeToggle";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

export function AppBar() {
  const setView = useViewStore((s) => s.setView);
  return (
    <nav className="flex shrink-0 items-center gap-4 border-b bg-card px-4 py-2">
      <span className="text-sm font-semibold">🥁 Drummer</span>
      <WorkspaceSwitcher />
      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          onClick={() => setView("tutorial")}
          className="rounded px-3 py-1 text-xs text-muted-foreground hover:text-foreground"
        >
          Tutorial
        </button>
        <ThemeToggle />
      </div>
    </nav>
  );
}
```

- [ ] **Step 6: Run full frontend checks**

Run: `cd frontend && npm run check && npx vitest run`
Expected: PASS (all suites).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/layout/ThemeToggle.tsx frontend/src/components/layout/ThemeToggle.test.tsx frontend/src/components/layout/AppBar.tsx
git commit -m "feat(frontend): ThemeToggle dropdown wired into AppBar"
```

---

## Task 7: Frontend — theme-following CodeMirror editors

**Files:**
- Create: `frontend/src/lib/editorTheme.ts`
- Modify: `frontend/src/components/request/ScriptTab.tsx`
- Modify: `frontend/src/components/request/BodyTab.tsx`
- Modify: `frontend/src/components/request/GraphQLTab.tsx`
- Modify: `frontend/src/components/request/UrlBar.tsx`

- [ ] **Step 1: Create the editor-theme helper**

Create `frontend/src/lib/editorTheme.ts`:

```typescript
import { oneDark } from "@codemirror/theme-one-dark";
import type { Extension } from "@codemirror/state";
import type { ResolvedTheme } from "../store/themeStore";

/** CodeMirror theme extension for the resolved app theme. Light = built-in default. */
export function editorThemeExtension(resolved: ResolvedTheme): Extension {
  return resolved === "dark" ? oneDark : [];
}
```

- [ ] **Step 2: Make ScriptTab follow the theme**

In `frontend/src/components/request/ScriptTab.tsx`:

Replace the `oneDark` import:

```typescript
import { oneDark } from "@codemirror/theme-one-dark";
```

with:

```typescript
import { Compartment } from "@codemirror/state";
import { editorThemeExtension } from "../../lib/editorTheme";
import { useResolvedTheme } from "../../store/themeStore";
```

Inside the component, add a compartment ref and read the resolved theme (near the other refs):

```typescript
  const themeCompartment = useRef(new Compartment());
  const resolved = useResolvedTheme();
```

In the one-time init `extensions` array, replace the bare `oneDark,` line with:

```typescript
          themeCompartment.current.of(editorThemeExtension(resolved)),
```

> Because the init effect uses refs and runs once, capture the initial `resolved` via a ref to avoid a stale-closure lint issue: add `const initialResolvedRef = useRef(resolved);` next to `initialScriptRef`, and use `editorThemeExtension(initialResolvedRef.current)` in the init array.

Add a reconfigure effect after the "Sync editor content when mode switches" effect:

```typescript
  useEffect(() => {
    viewRef.current?.dispatch({
      effects: themeCompartment.current.reconfigure(editorThemeExtension(resolved)),
    });
  }, [resolved]);
```

- [ ] **Step 3: Make BodyTab, GraphQLTab, UrlBar follow the theme**

For each of `BodyTab.tsx`, `GraphQLTab.tsx` (both editor instances), and `UrlBar.tsx`:

1. Add imports:
```typescript
import { Compartment } from "@codemirror/state";
import { editorThemeExtension } from "../../lib/editorTheme";
import { useResolvedTheme } from "../../store/themeStore";
```
2. Add near the refs:
```typescript
  const themeCompartment = useRef(new Compartment());
  const resolved = useResolvedTheme();
  const initialResolvedRef = useRef(resolved);
```
   (GraphQLTab has two editors — use two compartments, e.g. `queryThemeCompartment` and `varsThemeCompartment`, or one per `EditorView`.)
3. In each editor's `extensions` array, add after `basicSetup,`:
```typescript
          themeCompartment.current.of(editorThemeExtension(initialResolvedRef.current)),
```
4. Add a reconfigure effect per view:
```typescript
  useEffect(() => {
    viewRef.current?.dispatch({
      effects: themeCompartment.current.reconfigure(editorThemeExtension(resolved)),
    });
  }, [resolved]);
```
   (Match the existing `viewRef` name(s) in each file; GraphQLTab will have two.)

- [ ] **Step 4: Run frontend checks**

Run: `cd frontend && npm run check && npx vitest run`
Expected: PASS. (`UrlBar.test.tsx` must stay green — its render path now reads `useResolvedTheme`, which defaults to light.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/editorTheme.ts frontend/src/components/request/ScriptTab.tsx frontend/src/components/request/BodyTab.tsx frontend/src/components/request/GraphQLTab.tsx frontend/src/components/request/UrlBar.tsx
git commit -m "feat(frontend): CodeMirror editors follow the active theme via Compartment"
```

---

## Color Tokenization (Tasks 8–11)

**Mapping rules** — apply consistently. Hardcoded neutral colors → tokens:

| Hardcoded | Token class |
|---|---|
| `bg-white` (page/panel) | `bg-background` or `bg-card` (cards/raised) |
| `bg-gray-50` / `bg-gray-100` | `bg-muted` |
| `bg-gray-200` (chips/dividers) | `bg-muted` or `bg-border` |
| `bg-gray-700` / `800` / `900` / `950` (dark chrome) | `bg-card` / `bg-muted` / `bg-background` (pick by elevation) |
| `text-gray-900` / `800` | `text-foreground` |
| `text-gray-700` / `600` | `text-foreground` (primary) or `text-muted-foreground` (secondary) |
| `text-gray-500` / `400` | `text-muted-foreground` |
| `border-gray-200` / `300` / `700` / `800` | `border-border` (or just `border`) |
| `bg-blue-600` / `bg-blue-700` (primary action) | `bg-primary` (+ `text-primary-foreground`, `hover:bg-primary/90`) |
| `text-blue-300` / active-tab blue | `text-primary` / `border-primary` |
| `ring-*` neutral | `ring-ring` |

**Semantic colors keep their hue but gain dark variants** (do NOT flatten to grayscale): status green/yellow/red, variable-chip purple/amber, script-error red, hint amber. Pattern: add a `dark:` variant with a translucent bg + lighter text.

**Per-task verification (all sweep tasks):**
- `cd frontend && npm run check` → PASS (biome + tsc).
- `npx vitest run` → all suites PASS (StatusBadge, VariableChip, UrlBar tests included).
- Grep the touched files for leftover hardcoded colors (expected: no matches except intentional `dark:`/semantic lines):
  `grep -nE '(bg|text|border|ring)-(white|gray|slate|zinc|neutral)-' <files>`

---

## Task 8: Tokenize — layout chrome

**Files (Modify):** `frontend/src/views/WorkspaceView.tsx`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/layout/PanelGroup.tsx`, `frontend/src/components/layout/WorkspaceSwitcher.tsx`.

(`AppBar.tsx` and `App.tsx` loading screens were already tokenized in Tasks 5–6.)

- [ ] **Step 1: Convert each file** using the mapping rules above. Example — `WorkspaceSwitcher.tsx` external badge:

Replace:
```typescript
                <span className="rounded bg-gray-200 px-1 text-[10px] text-gray-600">
                  external
                </span>
```
with:
```typescript
                <span className="rounded bg-muted px-1 text-[10px] text-muted-foreground">
                  external
                </span>
```

Apply equivalent swaps to `WorkspaceView.tsx`, `Sidebar.tsx`, `PanelGroup.tsx`.

- [ ] **Step 2: Verify** — run the per-task verification block (npm run check, vitest, grep on these four files).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/WorkspaceView.tsx frontend/src/components/layout/Sidebar.tsx frontend/src/components/layout/PanelGroup.tsx frontend/src/components/layout/WorkspaceSwitcher.tsx
git commit -m "refactor(frontend): tokenize layout chrome colors"
```

---

## Task 9: Tokenize — request components

**Files (Modify):** `UrlBar.tsx`, `ParamsTab.tsx`, `HeadersTab.tsx`, `BodyTab.tsx`, `AuthTab.tsx`, `CookiesTab.tsx`, `GraphQLTab.tsx`, `ScriptTab.tsx`, `KeyValueTable.tsx`, `SchemaExplorer.tsx` (all under `frontend/src/components/request/`).

- [ ] **Step 1: Convert each file** using the mapping rules. Example — `ScriptTab.tsx` tab buttons + output:

Replace:
```typescript
      <div className="flex shrink-0 gap-1 border-b border-gray-700 px-2 pt-1">
```
with:
```typescript
      <div className="flex shrink-0 gap-1 border-b px-2 pt-1">
```
Replace the active/inactive tab classes:
```typescript
                ? "bg-gray-700 text-white"
                : "text-gray-400 hover:text-gray-200"
```
with:
```typescript
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:text-foreground"
```
Replace the script-output panel + semantic lines:
```typescript
        <div className="max-h-40 shrink-0 overflow-y-auto border-t border-gray-700 bg-gray-900 p-2 font-mono text-xs">
          {logEntries.map(({ key, text }) => (
            <div key={key} className="text-gray-300">
```
with:
```typescript
        <div className="max-h-40 shrink-0 overflow-y-auto border-t bg-muted p-2 font-mono text-xs">
          {logEntries.map(({ key, text }) => (
            <div key={key} className="text-muted-foreground">
```
and keep the semantic error/hint with dark variants:
```typescript
            <div className="mt-1 text-red-600 dark:text-red-400">{scriptError}</div>
```
```typescript
            <div className="mt-1 text-amber-600 dark:text-amber-400">Hint: {scriptSuggestion}</div>
```

Apply equivalent swaps across the other request files (SchemaExplorer is the densest — work top to bottom).

- [ ] **Step 2: Verify** — per-task verification block on these files.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/request/
git commit -m "refactor(frontend): tokenize request component colors"
```

---

## Task 10: Tokenize — response, tree, and shared components

**Files (Modify):** `frontend/src/components/response/*` (`ResponseMeta.tsx`, `HeadersViewer.tsx`, `RawViewer.tsx`, `BodyViewer.tsx`, `HistoryDrawer.tsx`, `ScriptOutput.tsx`), `frontend/src/components/tree/*` (`TreeNode.tsx`, `RequestTree.tsx`), `frontend/src/components/shared/*` (`StatusBadge.tsx`, `VariableChip.tsx`).

- [ ] **Step 1: Convert StatusBadge to dark-aware semantic colors**

Replace the `colourClass` function in `frontend/src/components/shared/StatusBadge.tsx`:

```typescript
function colourClass(code: number): string {
  if (code >= 200 && code < 300)
    return "bg-green-100 text-green-800 dark:bg-green-500/15 dark:text-green-300";
  if (code >= 300 && code < 400)
    return "bg-yellow-100 text-yellow-800 dark:bg-yellow-500/15 dark:text-yellow-300";
  return "bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300";
}
```

- [ ] **Step 2: Convert VariableChip to dark-aware semantic colors**

Replace the className ternary in `frontend/src/components/shared/VariableChip.tsx`:

```typescript
        isKnown
          ? "bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300"
          : "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300"
```

- [ ] **Step 3: Convert the response + tree files** using the mapping rules. Example — `ResponseMeta.tsx` neutral text:

Replace `text-gray-400` / `text-gray-500` occurrences with `text-muted-foreground`, and `border-b` neutral borders resolve via the token border automatically (the `*` base rule applies `border-border`).

- [ ] **Step 4: Verify** — per-task verification block; confirm `StatusBadge.test.tsx` and `VariableChip.test.tsx` pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/response/ frontend/src/components/tree/ frontend/src/components/shared/
git commit -m "refactor(frontend): tokenize response/tree/shared colors with dark semantic variants"
```

---

## Task 11: Tokenize TutorialView + add ThemeToggle to its nav

**Files:**
- Modify: `frontend/src/views/TutorialView.tsx`
- Create: `frontend/src/views/TutorialView.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/views/TutorialView.test.tsx`:

```typescript
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TutorialView } from "./TutorialView";

vi.mock("../api/settings", () => ({
  useSetTheme: () => ({ mutate: vi.fn() }),
}));

function renderTutorial() {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <TutorialView />
    </QueryClientProvider>,
  );
}

describe("TutorialView", () => {
  it("renders the theme toggle in its nav", () => {
    renderTutorial();
    expect(screen.getByLabelText(/theme/i)).toBeInTheDocument();
  });

  it("is not hardcoded to a dark background", () => {
    const { container } = renderTutorial();
    const root = container.querySelector("div");
    expect(root?.className).not.toContain("bg-gray-950");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/views/TutorialView.test.tsx`
Expected: FAIL — no element with accessible name "Theme", and the root still has `bg-gray-950`.

- [ ] **Step 3: Tokenize TutorialView**

In `frontend/src/views/TutorialView.tsx`:

1. Add import:
```typescript
import { ThemeToggle } from "../components/layout/ThemeToggle";
```
2. Root container — replace `bg-gray-950 text-gray-100` with `bg-background text-foreground`.
3. Nav bar — replace `border-gray-800 bg-gray-900` with `border-b bg-card`; logo `text-gray-200` → `text-foreground`. Add the toggle at the end of the nav, after the tab buttons:
```typescript
        <ThemeToggle />
```
   Wrap the existing tab `<div className="flex gap-1">` and the toggle so the toggle sits at the right: change the nav to include `ml-auto` on a wrapper, e.g. put `<div className="ml-auto"><ThemeToggle /></div>`.
4. Tab buttons — Workspace: `text-gray-400 hover:text-gray-200` → `text-muted-foreground hover:text-foreground`; active Tutorial: `bg-gray-700 text-white` → `bg-muted text-foreground`.
5. Left column — `border-gray-800 bg-gray-900` → `border-r bg-card`; the `PROGRESS`/`Instructions` labels `text-gray-500` → `text-muted-foreground`; instructions body `text-gray-300` → `text-muted-foreground`.
6. Step list active/done/idle — active `border-blue-700 bg-blue-900/50 text-blue-300` → `border border-primary bg-primary/10 text-primary`; done `bg-green-900/20 text-green-400` → `bg-green-500/10 text-green-700 dark:text-green-400`; idle `text-gray-500 hover:text-gray-300` → `text-muted-foreground hover:text-foreground`.
7. Back/Next buttons — Back `bg-gray-800 text-gray-400 hover:text-gray-200` → `bg-muted text-muted-foreground hover:text-foreground`; Next `bg-blue-600 ... hover:bg-blue-700` → `bg-primary text-primary-foreground hover:bg-primary/90`.
8. Request card — `bg-gray-800` → `bg-muted`; method pill `bg-blue-800 text-blue-200` → `bg-primary/15 text-primary`; url `text-gray-200` → `text-foreground`; Send `bg-blue-600 ... hover:bg-blue-700` → `bg-primary text-primary-foreground hover:bg-primary/90`.
9. **Response wrapper — drop the hardcoded light card:** replace `border border-gray-200 bg-white` with `border bg-card` so the shared (now tokenized) response components theme correctly.
10. Empty-state text `text-gray-500` → `text-muted-foreground`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/views/TutorialView.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Verify no leftover hardcoded colors**

Run: `grep -nE '(bg|text|border)-(white|gray|slate|blue)-' frontend/src/views/TutorialView.tsx`
Expected: no matches (semantic green lines retain `green-` with `dark:` — that's fine; confirm only intentional semantic lines remain).

- [ ] **Step 6: Full frontend gate**

Run: `cd frontend && npm run check && npx vitest run`
Expected: PASS (all suites).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/TutorialView.tsx frontend/src/views/TutorialView.test.tsx
git commit -m "refactor(frontend): tokenize TutorialView; theme toggle in tutorial nav"
```

---

## Task 12: Docs + final gate + milestone push

**Files:**
- Modify: `ROADMAP.md`, `CLAUDE.md`, `README.md`

- [ ] **Step 1: Update ROADMAP.md** — change the Phase 12 row Status from `⬜ Planned` to `🚧 In progress`.

- [ ] **Step 2: Update CLAUDE.md** — change `Current phase: **11 — Workspaces**` to `Current phase: **12 — Theming**`.

- [ ] **Step 3: Update README.md** — add a short note under the relevant UI/usage section:

```markdown
### Theming

Drummer supports light, dark, and system-auto themes. Use the theme toggle in the
top app bar (or the tutorial's nav). Your choice is saved to `~/.drummer/config.yaml`
and applies across the app and the tutorial.
```

- [ ] **Step 4: Run the full project gate**

Run: `make check`
Expected: PASS — ruff + pyright + `cd frontend && npm run check` + pytest (unit + integration) all green.

- [ ] **Step 5: Build the frontend to confirm it compiles for distribution**

Run: `make build-frontend`
Expected: Vite build succeeds (the static bundle is gitignored — do not commit it).

- [ ] **Step 6: Commit docs**

```bash
git add ROADMAP.md CLAUDE.md README.md
git commit -m "docs: Phase 12 theming — mark in progress, document theme toggle"
```

- [ ] **Step 7: Push the milestone**

```bash
git push origin main
```

(Per standing solo-team preference: commit directly to main, push at the milestone.)

---

## Self-Review notes (already reconciled)

- **Spec coverage:** modes/persistence (Tasks 1–5), toggle UI + placement (Tasks 6, 11), purple accent (Task 4), tokenization of both views including the dropped white card (Tasks 8–11), CodeMirror theming (Task 7), system-auto live updates (Task 5 `matchMedia`), no-flash first paint (Task 4 bootstrap + Task 5 gate), tests (each task), docs (Task 12). All spec sections map to a task.
- **Type consistency:** `ThemePref` is one Literal shared backend (`ws.ThemePref`) and frontend (`types.ts`); `Settings { theme }` matches between `settings.py` and `settings.ts`; `resolveTheme`/`useResolvedTheme`/`editorThemeExtension` signatures are consistent across Tasks 3, 5, 7.
- **No placeholders:** every code step shows the code; sweep tasks give explicit mapping rules + representative before/after + grep verification rather than vague "convert colors".
