# Phase 16 — Environment & Variable Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users create, delete, and edit the variables of environments from the app (today the UI only selects environments read-only, so `{{base_url}}` can't be set without hand-editing YAML).

**Architecture:** Add backend create/delete routes over the existing environment storage, two new React Query hooks, a small Base UI Dialog wrapper, and an `EnvironmentManager` modal (launched from a gear button next to the sidebar's environment selector) that edits one environment's variables via the existing `KeyValueTable`. Additive within existing layers — no ADR.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest + httpx `AsyncClient`; React 19, TypeScript, Vite, Zustand, TanStack Query, Base UI (`@base-ui/react`), Vitest + Testing Library, Biome.

**Critical process notes:**
- `make check` runs ruff + pyright + Biome + `tsc --noEmit` + the Python tests, but **NOT** the frontend vitest suite. For every task that touches frontend code, run `cd frontend && npx vitest run` AND `cd frontend && npx tsc -b` explicitly before committing (the pre-commit hook will not catch a broken vitest test, and `npm run build` uses the stricter `tsc -b`).
- In Vitest, never destructure `vi.mocked(apiFetch).mock.calls[0]` (fails `tsc -b` with TS2488). Use `toHaveBeenCalledWith(...)` or the safe accessor `vi.mocked(apiFetch).mock.calls[0]?.[1]`.
- No suppression comments (`# type: ignore`, `# noqa`, `biome-ignore`, `@ts-ignore`) and no TS non-null assertions (`!`). Fix at the root.
- End commit messages with the `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer.

---

## File Structure

**Backend**
- Modify `drummer/core/storage/project.py` — add `delete_environment` (Task 1).
- Modify `drummer/api/routes/environments.py` — add POST (Task 2) and DELETE (Task 3).
- Modify `tests/unit/test_project.py` — unit test for `delete_environment` (Task 1).
- Modify `tests/integration/test_environments_routes.py` — route tests (Tasks 2, 3).

**Frontend**
- Modify `frontend/src/api/environments.ts` — `useCreateEnvironment`, `useDeleteEnvironment` (Task 4).
- Create `frontend/src/api/environments.test.tsx` — hook tests (Task 4).
- Create `frontend/src/components/ui/dialog.tsx` — Base UI Dialog wrapper (Task 5).
- Create `frontend/src/components/layout/EnvironmentManager.tsx` — the modal (Task 6).
- Create `frontend/src/components/layout/EnvironmentManager.test.tsx` — component test (Task 6).
- Modify `frontend/src/components/layout/Sidebar.tsx` — gear button + render modal (Task 7).
- Modify `ROADMAP.md`, `TODO.md` — close-out (Task 8).

Ordering keeps every commit green: backend Tasks 1→2→3 are independent; frontend Task 4 (hooks) → 5 (dialog) → 6 (manager, imports 4 & 5) → 7 (sidebar, imports 6) → 8 (gate/docs).

---

## Task 1: Core `delete_environment` helper

**Files:**
- Modify: `drummer/core/storage/project.py`
- Test: `tests/unit/test_project.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_project.py` (it already imports from `drummer.core.storage.project` and uses `tmp_path`; mirror the existing environment tests' style — check the top of the file for the exact import form and reuse it):

```python
def test_delete_environment_removes_file(tmp_path: Path) -> None:
    from drummer.core.storage.project import (
        Environment,
        create_project,
        delete_environment,
        save_environment,
    )

    create_project(tmp_path, "P")
    save_environment(Environment(name="staging", variables={"k": "v"}), tmp_path)
    env_file = tmp_path / ".drummer" / "environments" / "staging.yaml"
    assert env_file.exists()

    delete_environment("staging", tmp_path)
    assert not env_file.exists()
```

(If `test_project.py` already imports these names at module scope, drop the inline import and rely on those. Match the file's existing pattern.)

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/unit/test_project.py -k delete_environment -v`
Expected: FAIL — `ImportError: cannot import name 'delete_environment'`.

- [ ] **Step 3: Implement**

In `drummer/core/storage/project.py`, add this function immediately after `save_environment`:

```python
def delete_environment(name: str, project_dir: Path) -> None:
    env_path = project_dir / ".drummer" / "environments" / f"{name}.yaml"
    env_path.unlink()
```

(The route layer is responsible for checking existence first and returning 404; this helper assumes the file exists.)

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/pytest tests/unit/test_project.py -k delete_environment -v`
Expected: PASS.

- [ ] **Step 5: Lint + commit**

Run: `venv/bin/ruff check drummer tests && venv/bin/ruff format --check . && venv/bin/pyright drummer`

```bash
git add drummer/core/storage/project.py tests/unit/test_project.py
git commit -m "feat(core): delete_environment storage helper (16)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `POST /api/environments` (create)

**Files:**
- Modify: `drummer/api/routes/environments.py`
- Test: `tests/integration/test_environments_routes.py`

Context: the route file already defines `EnvironmentSummary`, `EnvironmentDetail`, a `_safe_env_path(project_dir, name)` helper (raises 400 on traversal), `_ENV_NOT_FOUND`, and imports `Environment`, `list_environments`, `load_environment`, `save_environment` from `drummer.core.storage.project`, plus `HTTPStatus`, `HTTPException`, `BaseModel`, `Field`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/test_environments_routes.py` (check its top for the `client` fixture; it isolates `DRUMMER_HOME` and creates a project with a `local` env — reuse that fixture exactly as the existing tests do):

```python
async def test_create_environment(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/environments", json={"name": "staging", "variables": {"base_url": "https://s"}}
    )
    assert resp.status_code == HTTPStatus.CREATED
    assert resp.json() == {"name": "staging", "variables": {"base_url": "https://s"}}
    listed = {e["name"] for e in (await client.get("/api/environments")).json()}
    assert "staging" in listed


async def test_create_environment_duplicate_conflicts(client: AsyncClient) -> None:
    await client.post("/api/environments", json={"name": "staging", "variables": {}})
    resp = await client.post("/api/environments", json={"name": "staging", "variables": {}})
    assert resp.status_code == HTTPStatus.CONFLICT


async def test_create_environment_rejects_blank_name(client: AsyncClient) -> None:
    resp = await client.post("/api/environments", json={"name": "   ", "variables": {}})
    assert resp.status_code == HTTPStatus.BAD_REQUEST


async def test_create_environment_rejects_path_name(client: AsyncClient) -> None:
    resp = await client.post("/api/environments", json={"name": "../escape", "variables": {}})
    assert resp.status_code == HTTPStatus.BAD_REQUEST
```

(`AsyncClient` and `HTTPStatus` are already imported in that file.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/integration/test_environments_routes.py -k create -v`
Expected: FAIL — POST route returns 405/404 (not registered).

- [ ] **Step 3: Implement**

In `drummer/api/routes/environments.py`, add a request model after the existing `EnvironmentDetail` class:

```python
class CreateEnvironmentBody(BaseModel):
    name: str
    variables: dict[str, str] = Field(default_factory=dict)
```

Add this route after `list_environments_route` (the exact position among handlers doesn't matter; place it before the PUT handler for readability):

```python
@router.post("/environments", status_code=HTTPStatus.CREATED)
async def create_environment_route(
    body: CreateEnvironmentBody, project_dir: ProjectDir
) -> EnvironmentDetail:
    name = body.name.strip()
    if not name or "/" in name or "\\" in name or name in {".", ".."}:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Invalid environment name")
    env_path = _safe_env_path(project_dir, name)
    if env_path.exists():
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT, detail=f"Environment '{name}' already exists"
        )
    env = Environment(name=name, variables=body.variables)
    save_environment(env, project_dir)
    return EnvironmentDetail(name=env.name, variables=env.variables)
```

(`_safe_env_path` is the existing backstop against traversal; the explicit checks give a clear 400 for blank/`/`/`..` before it.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/integration/test_environments_routes.py -v`
Expected: PASS (all environment-route tests).

- [ ] **Step 5: Lint + commit**

Run: `venv/bin/ruff check drummer tests && venv/bin/ruff format --check . && venv/bin/pyright drummer`

```bash
git add drummer/api/routes/environments.py tests/integration/test_environments_routes.py
git commit -m "feat(api): POST /environments to create an environment (16)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `DELETE /api/environments/{name}`

**Files:**
- Modify: `drummer/api/routes/environments.py`
- Test: `tests/integration/test_environments_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/test_environments_routes.py`:

```python
async def test_delete_environment(client: AsyncClient) -> None:
    await client.post("/api/environments", json={"name": "staging", "variables": {}})
    resp = await client.delete("/api/environments/staging")
    assert resp.status_code == HTTPStatus.NO_CONTENT
    listed = {e["name"] for e in (await client.get("/api/environments")).json()}
    assert "staging" not in listed


async def test_delete_missing_environment_returns_404(client: AsyncClient) -> None:
    resp = await client.delete("/api/environments/ghost")
    assert resp.status_code == HTTPStatus.NOT_FOUND
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/integration/test_environments_routes.py -k delete -v`
Expected: FAIL — DELETE route not registered.

- [ ] **Step 3: Implement**

In `drummer/api/routes/environments.py`, add `delete_environment` to the existing import from `drummer.core.storage.project` (it currently imports `Environment, list_environments, load_environment, save_environment`):

```python
from drummer.core.storage.project import (
    Environment,
    delete_environment,
    list_environments,
    load_environment,
    save_environment,
)
```

Add the route after the PUT handler:

```python
@router.delete("/environments/{name}", status_code=HTTPStatus.NO_CONTENT)
async def delete_environment_route(name: str, project_dir: ProjectDir) -> None:
    env_path = _safe_env_path(project_dir, name)
    if not env_path.exists():
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=_ENV_NOT_FOUND)
    delete_environment(name, project_dir)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/integration/test_environments_routes.py -v`
Expected: PASS.

- [ ] **Step 5: Lint + commit**

Run: `venv/bin/ruff check drummer tests && venv/bin/ruff format --check . && venv/bin/pyright drummer`

```bash
git add drummer/api/routes/environments.py tests/integration/test_environments_routes.py
git commit -m "feat(api): DELETE /environments/{name} (16)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: `useCreateEnvironment` + `useDeleteEnvironment` hooks

**Files:**
- Modify: `frontend/src/api/environments.ts`
- Test: `frontend/src/api/environments.test.tsx` (create)

Context: `environments.ts` already imports `useMutation, useQuery, useQueryClient` from `@tanstack/react-query`, `EnvironmentDetail`/`EnvironmentSummary` from `../types`, and `apiFetch` from `./client`. It already has `useEnvironments`, `useEnvironment`, `useSaveEnvironment`.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/api/environments.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "./client";
import { useCreateEnvironment, useDeleteEnvironment } from "./environments";

vi.mock("./client", () => ({ apiFetch: vi.fn() }));

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useCreateEnvironment", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it("POSTs name and variables to /api/environments", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ name: "staging", variables: { a: "b" } });
    const { result } = renderHook(() => useCreateEnvironment(), { wrapper });
    await result.current.mutateAsync({ name: "staging", variables: { a: "b" } });
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));
    expect(apiFetch).toHaveBeenCalledWith(
      "/api/environments",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "staging", variables: { a: "b" } }),
      }),
    );
  });
});

describe("useDeleteEnvironment", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it("DELETEs /api/environments/{name}", async () => {
    vi.mocked(apiFetch).mockResolvedValue(undefined);
    const { result } = renderHook(() => useDeleteEnvironment(), { wrapper });
    await result.current.mutateAsync("staging");
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));
    expect(apiFetch).toHaveBeenCalledWith(
      "/api/environments/staging",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/api/environments.test.tsx`
Expected: FAIL — hooks not exported.

- [ ] **Step 3: Implement**

In `frontend/src/api/environments.ts`, add after `useSaveEnvironment` (reuse the existing imports):

```typescript
export function useCreateEnvironment() {
  const queryClient = useQueryClient();
  return useMutation<
    EnvironmentDetail,
    Error,
    { name: string; variables: Record<string, string> }
  >({
    mutationFn: ({ name, variables }) =>
      apiFetch<EnvironmentDetail>("/api/environments", {
        method: "POST",
        body: JSON.stringify({ name, variables }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["environments"] });
    },
  });
}

export function useDeleteEnvironment() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (name) =>
      apiFetch<void>(`/api/environments/${name}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["environments"] });
    },
  });
}
```

- [ ] **Step 4: Run test + typecheck**

Run: `cd frontend && npx vitest run src/api/environments.test.tsx` → PASS.
Run: `cd frontend && npx tsc -b` → no errors.
Run: `cd frontend && npm run check` → clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/environments.ts frontend/src/api/environments.test.tsx
git commit -m "feat(frontend): useCreateEnvironment + useDeleteEnvironment hooks (16)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: `Dialog` UI primitive (Base UI wrapper)

**Files:**
- Create: `frontend/src/components/ui/dialog.tsx`

Context: the project wraps Base UI primitives shadcn-style (see `frontend/src/components/ui/select.tsx`: `"use client"`, `import { X as XPrimitive } from "@base-ui/react/x"`, `cn` from `@/lib/utils`, components tagged with `data-slot`). Base UI exposes `Dialog.Root`, `Dialog.Trigger`, `Dialog.Portal`, `Dialog.Backdrop`, `Dialog.Popup`, `Dialog.Title`, `Dialog.Description`, `Dialog.Close`.

- [ ] **Step 1: Create the wrapper**

Create `frontend/src/components/ui/dialog.tsx`:

```tsx
"use client";

import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";
import type * as React from "react";
import { cn } from "@/lib/utils";

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogClose = DialogPrimitive.Close;

function DialogPopup({
  className,
  children,
  ...props
}: DialogPrimitive.Popup.Props) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Backdrop
        data-slot="dialog-backdrop"
        className="fixed inset-0 z-50 bg-black/40 data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0"
      />
      <DialogPrimitive.Popup
        data-slot="dialog-popup"
        className={cn(
          "fixed top-1/2 left-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border bg-popover p-4 text-popover-foreground shadow-lg outline-none data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95",
          className,
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Popup>
    </DialogPrimitive.Portal>
  );
}

function DialogTitle({ className, ...props }: DialogPrimitive.Title.Props) {
  return (
    <DialogPrimitive.Title
      data-slot="dialog-title"
      className={cn("text-sm font-semibold", className)}
      {...props}
    />
  );
}

export { Dialog, DialogClose, DialogPopup, DialogTitle, DialogTrigger };
```

> Adaptation note: this targets `@base-ui/react` 1.5.0. If a prop-type name differs (e.g. `DialogPrimitive.Popup.Props`), run `cd frontend && npx tsc -b` and correct it to whatever the installed types export — the structure (Portal → Backdrop + Popup, Title) stays the same. Do not add suppression comments to paper over a type mismatch.

- [ ] **Step 2: Verify it type-checks**

Run: `cd frontend && npx tsc -b` → no errors.
Run: `cd frontend && npm run check` → clean (Biome may reformat the long class string; accept its formatting).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/dialog.tsx
git commit -m "feat(frontend): Dialog UI primitive over Base UI (16)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: `EnvironmentManager` modal component

**Files:**
- Create: `frontend/src/components/layout/EnvironmentManager.tsx`
- Test: `frontend/src/components/layout/EnvironmentManager.test.tsx` (create)

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/layout/EnvironmentManager.test.tsx`. The env-api module is mocked with stable references via `vi.hoisted` (so the `useEnvironment` detail object keeps a stable identity across renders — otherwise the draft-sync effect would reset on every render):

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EnvironmentManager } from "./EnvironmentManager";

const h = vi.hoisted(() => ({
  list: [
    { name: "local", variable_count: 1 },
    { name: "staging", variable_count: 0 },
  ],
  detail: { name: "local", variables: { base_url: "https://api" } },
  saveMutate: vi.fn(),
  createMutate: vi.fn(),
  deleteMutate: vi.fn(),
}));

vi.mock("../../api/environments", () => ({
  useEnvironments: () => ({ data: h.list }),
  useEnvironment: () => ({ data: h.detail }),
  useSaveEnvironment: () => ({ mutate: h.saveMutate }),
  useCreateEnvironment: () => ({ mutate: h.createMutate }),
  useDeleteEnvironment: () => ({ mutate: h.deleteMutate }),
}));

describe("EnvironmentManager", () => {
  beforeEach(() => {
    h.saveMutate.mockReset();
    h.createMutate.mockReset();
    h.deleteMutate.mockReset();
  });

  it("renders the selected environment's variables", () => {
    render(<EnvironmentManager open onClose={vi.fn()} />);
    expect(screen.getByDisplayValue("base_url")).toBeInTheDocument();
    expect(screen.getByDisplayValue("https://api")).toBeInTheDocument();
  });

  it("Save sends the edited variables", () => {
    render(<EnvironmentManager open onClose={vi.fn()} />);
    fireEvent.change(screen.getByDisplayValue("https://api"), {
      target: { value: "https://api/v2" },
    });
    fireEvent.click(screen.getByTestId("env-save-button"));
    expect(h.saveMutate).toHaveBeenCalledWith({
      name: "local",
      variables: { base_url: "https://api/v2" },
    });
  });

  it("+ New creates an environment from the prompted name", () => {
    vi.spyOn(window, "prompt").mockReturnValue("qa");
    render(<EnvironmentManager open onClose={vi.fn()} />);
    fireEvent.click(screen.getByTestId("env-new-button"));
    expect(h.createMutate.mock.calls[0]?.[0]).toEqual({ name: "qa", variables: {} });
  });

  it("Delete removes the selected environment after confirm", () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<EnvironmentManager open onClose={vi.fn()} />);
    fireEvent.click(screen.getByTestId("env-delete-button"));
    expect(h.deleteMutate.mock.calls[0]?.[0]).toBe("local");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/layout/EnvironmentManager.test.tsx`
Expected: FAIL — module `./EnvironmentManager` does not exist.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/layout/EnvironmentManager.tsx`:

```tsx
import { useEffect, useState } from "react";
import {
  useCreateEnvironment,
  useDeleteEnvironment,
  useEnvironment,
  useEnvironments,
  useSaveEnvironment,
} from "../../api/environments";
import { useSessionStore } from "../../store/sessionStore";
import { KeyValueTable } from "../request/KeyValueTable";
import { Dialog, DialogPopup, DialogTitle } from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";

interface EnvironmentManagerProps {
  open: boolean;
  onClose: () => void;
}

export function EnvironmentManager({ open, onClose }: EnvironmentManagerProps) {
  const { data: environments = [] } = useEnvironments();
  const activeEnvironment = useSessionStore((s) => s.activeEnvironment);
  const setActiveEnvironment = useSessionStore((s) => s.setActiveEnvironment);

  const createEnv = useCreateEnvironment();
  const deleteEnv = useDeleteEnvironment();
  const saveEnv = useSaveEnvironment();

  const [editingName, setEditingName] = useState<string>("");
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const { data: detail } = useEnvironment(editingName || null);

  // On open, default the editing target to the active env (or the first one).
  useEffect(() => {
    if (!open) return;
    const names = environments.map((e) => e.name);
    setError(null);
    setEditingName((prev) => {
      if (prev && names.includes(prev)) return prev;
      if (names.includes(activeEnvironment)) return activeEnvironment;
      return names[0] ?? "";
    });
  }, [open, environments, activeEnvironment]);

  // Sync the selected env's variables into the local draft.
  useEffect(() => {
    if (detail) setDraft(detail.variables);
  }, [detail]);

  const isDirty =
    detail !== undefined &&
    JSON.stringify(draft) !== JSON.stringify(detail.variables);

  const switchEnv = (next: string) => {
    if (isDirty && !window.confirm("Discard unsaved variable changes?")) return;
    setError(null);
    setEditingName(next);
  };

  const handleSave = () => {
    if (!editingName) return;
    saveEnv.mutate({ name: editingName, variables: draft });
  };

  const handleNew = () => {
    const name = window.prompt("New environment name:")?.trim();
    if (!name) return;
    if (environments.some((e) => e.name === name)) {
      setError(`An environment named '${name}' already exists`);
      return;
    }
    createEnv.mutate(
      { name, variables: {} },
      {
        onSuccess: () => {
          setError(null);
          setEditingName(name);
        },
        onError: () => setError(`Could not create '${name}'`),
      },
    );
  };

  const handleDelete = () => {
    if (!editingName) return;
    if (
      !window.confirm(`Delete environment '${editingName}'? This cannot be undone.`)
    )
      return;
    const deleted = editingName;
    deleteEnv.mutate(deleted, {
      onSuccess: () => {
        const remaining = environments
          .map((e) => e.name)
          .filter((n) => n !== deleted);
        if (activeEnvironment === deleted) {
          setActiveEnvironment(remaining[0] ?? "local");
        }
        setEditingName(remaining[0] ?? "");
      },
    });
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        if (!isOpen) onClose();
      }}
    >
      <DialogPopup className="flex flex-col gap-3">
        <DialogTitle>Manage Environments</DialogTitle>

        <div className="flex items-center gap-2">
          <Select value={editingName} onValueChange={(v) => v && switchEnv(v)}>
            <SelectTrigger size="sm" className="min-w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {environments.map((e) => (
                <SelectItem key={e.name} value={e.name}>
                  {e.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <button
            type="button"
            className="rounded border px-2 py-1 text-xs hover:bg-muted"
            onClick={handleNew}
            data-testid="env-new-button"
          >
            + New
          </button>
          <button
            type="button"
            className="rounded border px-2 py-1 text-xs text-destructive hover:bg-muted disabled:opacity-40"
            onClick={handleDelete}
            disabled={!editingName}
            data-testid="env-delete-button"
          >
            Delete
          </button>
        </div>

        {error && (
          <p className="text-xs text-destructive" role="alert">
            {error}
          </p>
        )}

        {editingName ? (
          <KeyValueTable
            entries={draft}
            onChange={setDraft}
            keyPlaceholder="Variable"
            valuePlaceholder="Value"
          />
        ) : (
          <p className="px-2 py-4 text-xs text-muted-foreground">
            No environment selected. Create one with “+ New”.
          </p>
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            className="rounded border px-3 py-1.5 text-sm hover:bg-muted"
            onClick={onClose}
          >
            Close
          </button>
          <button
            type="button"
            className="rounded bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-40"
            onClick={handleSave}
            disabled={!editingName || !isDirty}
            data-testid="env-save-button"
          >
            Save
          </button>
        </div>
      </DialogPopup>
    </Dialog>
  );
}
```

> If the Base UI `Select`'s `onValueChange` value type is `string | null` (it is, per `WorkspaceSwitcher.tsx`), the `(v) => v && switchEnv(v)` guard handles null. If `tsc -b` complains about the `Dialog` `onOpenChange` signature, match it to the installed Base UI type (the intent: call `onClose()` when the dialog requests close).

- [ ] **Step 4: Run tests + typecheck**

Run: `cd frontend && npx vitest run src/components/layout/EnvironmentManager.test.tsx` → PASS (4 tests).
Run: `cd frontend && npx tsc -b` → no errors.
Run: `cd frontend && npm run check` → clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/EnvironmentManager.tsx frontend/src/components/layout/EnvironmentManager.test.tsx
git commit -m "feat(frontend): EnvironmentManager modal (edit vars, create, delete) (16)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Wire the modal into the Sidebar

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx`

Context: `Sidebar` already takes `onRequestSelect`, `onRequestDelete`, `onNewRequest` (Phase 15) and renders the Project block, an Environment block (currently shown only when `environments.length > 0`), and the Requests tree. We add a gear button (always visible) that opens the `EnvironmentManager` modal.

- [ ] **Step 1: Replace the file**

Replace the entire contents of `frontend/src/components/layout/Sidebar.tsx` with:

```tsx
import { Settings } from "lucide-react";
import { useState } from "react";
import { useEnvironments } from "../../api/environments";
import { useProjectStore } from "../../store/projectStore";
import { useSessionStore } from "../../store/sessionStore";
import { RequestTree } from "../tree/RequestTree";
import { EnvironmentManager } from "./EnvironmentManager";

interface SidebarProps {
  onRequestSelect: (path: string) => void;
  onRequestDelete: (path: string) => void;
  onNewRequest: () => void;
}

export function Sidebar({
  onRequestSelect,
  onRequestDelete,
  onNewRequest,
}: SidebarProps) {
  const project = useProjectStore((s) => s.project);
  const requests = useProjectStore((s) => s.requests);
  const activeEnvironment = useSessionStore((s) => s.activeEnvironment);
  const setActiveEnvironment = useSessionStore((s) => s.setActiveEnvironment);
  const { data: environments = [] } = useEnvironments();
  const [manageOpen, setManageOpen] = useState(false);

  return (
    <div className="flex h-full flex-col border-r bg-sidebar">
      <div className="border-b px-3 py-2">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Project
        </p>
        <p className="truncate text-sm font-medium text-foreground">
          {project?.name}
        </p>
      </div>

      <div className="border-b px-3 py-2">
        <div className="flex items-center justify-between">
          <label
            htmlFor="environment-select"
            className="text-xs text-muted-foreground"
          >
            Environment
          </label>
          <button
            type="button"
            className="rounded p-0.5 text-muted-foreground hover:text-foreground"
            onClick={() => setManageOpen(true)}
            aria-label="Manage environments"
            data-testid="manage-environments-button"
          >
            <Settings size={14} />
          </button>
        </div>
        {environments.length > 0 && (
          <select
            id="environment-select"
            className="mt-1 w-full rounded border px-2 py-1 text-sm"
            value={activeEnvironment}
            onChange={(e) => setActiveEnvironment(e.target.value)}
          >
            {environments.map((env) => (
              <option key={env.name} value={env.name}>
                {env.name}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="flex items-center justify-between border-b px-3 py-1.5">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Requests
        </span>
        <button
          type="button"
          className="rounded px-1.5 py-0.5 text-xs text-primary hover:bg-primary/10"
          onClick={onNewRequest}
          data-testid="new-request-button"
        >
          + New
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-1 py-1">
        <RequestTree
          requests={requests}
          onSelect={onRequestSelect}
          onDelete={onRequestDelete}
        />
      </div>

      <EnvironmentManager
        open={manageOpen}
        onClose={() => setManageOpen(false)}
      />
    </div>
  );
}
```

- [ ] **Step 2: Run the full frontend suite + typecheck**

Run: `cd frontend && npx vitest run` → ALL pass (no Sidebar/AppBar regressions).
Run: `cd frontend && npx tsc -b` → no errors.
Run: `cd frontend && npm run check` → clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/Sidebar.tsx
git commit -m "feat(frontend): gear button opens the Environment manager (16)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Full-suite gate, in-app verification note, docs

**Files:**
- Modify: `ROADMAP.md`, `TODO.md`

- [ ] **Step 1: Full gate**

Run: `make check` → all green (ruff, pyright, Biome, tsc, Python tests).
Run: `cd frontend && npx vitest run` → all frontend tests pass (remember `make check` does NOT run vitest).
Fix anything red at the root (no suppression comments), then re-run.

- [ ] **Step 2: Manual in-app verification (record what you observe)**

Build and run: `cd frontend && npm run build`, then start the server against a scratch/temp project (`DRUMMER_HOME=$(mktemp -d) venv/bin/python -m drummer.cli serve --project <tmpproj> --port 8765`). In the browser:
1. Click the gear next to the Environment selector → the modal opens.
2. Add a variable row (e.g. `base_url` = `https://x`), Save → reopen and confirm it persisted.
3. + New → name it → it becomes selectable; the sidebar selector lists it after close.
4. Delete an environment (confirm) → it disappears from both the modal and the sidebar selector; if it was active, the sidebar falls back to a remaining env.
Stop the server and remove the temp dirs when done.

- [ ] **Step 3: Update docs**

In `ROADMAP.md`, change the Phase 16 row status from `⏳ Planned` to `✅ Done`. In `TODO.md`, move Phase 16 from "Next" to "Done" with a one-line summary, and note Phase 17 (sent-request inspector) is the remaining planned phase.

- [ ] **Step 4: Commit**

```bash
git add ROADMAP.md TODO.md
git commit -m "docs: close out Phase 16 (environment & variable editor)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage:**
  - Backend POST create → Task 2; DELETE → Task 3; `delete_environment` core helper → Task 1. ✓
  - Name validation (blank/`/`/`..`) → Task 2 (tested). ✓
  - 409 on duplicate → Task 2. ✓
  - Frontend create/delete hooks → Task 4. ✓
  - Dialog primitive → Task 5; `EnvironmentManager` modal (edit via KeyValueTable, create, delete, dirty guard, inline error) → Task 6. ✓
  - Sidebar gear + always-visible Manage affordance → Task 7. ✓
  - Active-env fallback on delete → Task 6 (`handleDelete`). Note: spec said "default_environment → first remaining → local"; the frontend does not have `default_environment` exposed, so this plan uses **first remaining → "local"**. Documented deviation; acceptable UX (the active env is frontend session state).
  - Two-selectors distinction (modal edits vs sidebar active) → preserved (Task 6 modal Select vs Task 7 sidebar `<select>`). ✓
  - Testing per spec → Tasks 1–6 each include tests; Dialog primitive untested by design. ✓
- **Placeholder scan:** No TBD/TODO/"handle edge cases"; every code step has complete code. The only adaptation notes are for third-party (Base UI) prop-type names, with `tsc -b` as the gate — not placeholders.
- **Type consistency:** `useCreateEnvironment` arg `{ name, variables }` matches `CreateEnvironmentBody` and the EnvironmentManager `createEnv.mutate({ name, variables: {} })` call. `useDeleteEnvironment` takes a `string` name, matching `deleteEnv.mutate(deleted)` and the DELETE route. `delete_environment(name, project_dir)` signature matches its route caller and unit test. `EnvironmentManager` props `{ open, onClose }` match the Sidebar usage. `Dialog`/`DialogPopup`/`DialogTitle` exports match the EnvironmentManager imports.
