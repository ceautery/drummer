# F1, F2 & Phase 15 (Request Editing & CRUD) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the two immediate one-off fixes (F1 raw-tab redundancy, F2 forget-external-workspace + test isolation) and Phase 15 (fix the request-save data-loss/crash bug, add a visible Save affordance, and add new/delete request CRUD in the tree).

**Architecture:** Backend changes are confined to `drummer/api/routes/` and `drummer/core/storage/workspaces.py`; no new layer boundaries (no ADR). The critical save fix changes the `PUT /api/requests/{path}` contract to accept and return a full `RequestDetail` (whole `RequestFrontmatter` + body) instead of the lossy 5-field `CreateRequestBody`/`RequestSummary` pair. Frontend changes thread a Save handler and new/delete-request handlers down from `WorkspaceView` through `Sidebar`/`RequestResponseWorkbench`, reusing existing React Query + zustand patterns.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest + httpx `AsyncClient`; React 19, TypeScript, Vite, Zustand, TanStack Query, Vitest + Testing Library, Biome.

**Scope decisions (delegated from the spec):**
- **15d covers _new_ and _delete_ requests only.** File **rename** and **move/folders** are deferred to a later phase: all three require the same "move file" primitive (create-at-new-path + delete-old + fix selection/history), which is a coherent unit best done together later. Editing a request's display `name` is already possible (it is a frontmatter field) and saves through the normal save path.
- Each task is TDD: failing test → run (fail) → minimal code → run (pass) → commit. Run `make check` before each commit unless a step says otherwise.

---

## File Structure

**Backend**
- Modify `drummer/api/routes/requests.py` — replace lossy PUT contract with full-`RequestDetail` round-trip (15a/15b).
- Modify `drummer/core/storage/workspaces.py` — add `forget_external` (F2).
- Modify `drummer/api/routes/workspaces.py` — add `POST /workspaces/forget` (F2).
- Modify `tests/e2e/conftest.py` — isolate the spawned server's `DRUMMER_HOME` (F2).
- Modify `tests/integration/test_requests_routes.py` — update PUT test to new contract + add preservation regression (15a/15b).
- Modify `tests/unit/test_workspaces.py` — add `forget_external` tests (F2).
- Modify `tests/integration/test_workspaces_routes.py` — add forget-route test (F2).

**Frontend**
- Modify `frontend/src/components/response/RawViewer.tsx` — drop the redundant `<pre>` panel (F1); add `RawViewer.test.tsx`.
- Modify `frontend/src/api/requests.ts` — full-frontmatter save + `useCreateRequest` (15a/15b/15d); add `requests.test.tsx`.
- Modify `frontend/src/api/workspaces.ts` — `useForgetWorkspace` (F2).
- Modify `frontend/src/store/requestStore.ts` — add `deselect` (15d); add `requestStore.test.ts`.
- Modify `frontend/src/components/tree/TreeNode.tsx` — add delete affordance, de-nest buttons (15d); add `TreeNode.test.tsx`.
- Modify `frontend/src/components/tree/RequestTree.tsx` — thread `onDelete` (15d).
- Modify `frontend/src/components/layout/Sidebar.tsx` — "+ New request" button + thread delete (15d).
- Modify `frontend/src/components/layout/RequestResponseWorkbench.tsx` — thread `onSave`/`canSave` to `UrlBar` (15c).
- Modify `frontend/src/components/request/UrlBar.tsx` — Save button (15c).
- Modify `frontend/src/views/WorkspaceView.tsx` — wire create/delete/save handlers (15c/15d).
- Modify `frontend/src/components/layout/WorkspaceSwitcher.tsx` — "Forget external workspace" action (F2); update `WorkspaceSwitcher.test.tsx` mock.

---

## F1 — Raw response tab redundancy

### Task F1: Make the Raw tab a pure hexdump

**Files:**
- Modify: `frontend/src/components/response/RawViewer.tsx`
- Test: `frontend/src/components/response/RawViewer.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/response/RawViewer.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RawViewer } from "./RawViewer";

describe("RawViewer", () => {
  it("renders the body text exactly once (hexdump ASCII column only)", () => {
    render(<RawViewer body="hello" />);
    // Before the fix the body appeared twice: once in the hexdump ASCII
    // column and once in a standalone <pre> panel. It must now appear once.
    expect(screen.getAllByText("hello")).toHaveLength(1);
  });

  it("renders a hexdump table with an Offset header", () => {
    render(<RawViewer body="hello" />);
    expect(screen.getByText("Offset")).toBeInTheDocument();
  });

  it("renders nothing when body is null", () => {
    const { container } = render(<RawViewer body={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/response/RawViewer.test.tsx`
Expected: FAIL — `getAllByText("hello")` returns length 2 (ASCII column + `<pre>` panel).

- [ ] **Step 3: Remove the redundant `<pre>` panel**

Replace the entire contents of `frontend/src/components/response/RawViewer.tsx` with:

```tsx
import { hexdump } from "../../lib/hexdump";

interface RawViewerProps {
  body: string | null;
}

export function RawViewer({ body }: RawViewerProps) {
  if (body === null) return null;
  const rows = hexdump(body);

  return (
    <div className="h-full overflow-auto p-2">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b text-muted-foreground">
            <th className="px-2 py-1 text-left w-24">Offset</th>
            <th className="px-2 py-1 text-left">Hex</th>
            <th className="px-2 py-1 text-left w-32">ASCII</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.offset} className="border-b last:border-0">
              <td className="px-2 py-0.5 text-muted-foreground">
                {row.offset}
              </td>
              <td className="px-2 py-0.5 text-foreground">{row.hex}</td>
              <td className="px-2 py-0.5 text-muted-foreground">{row.ascii}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/response/RawViewer.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/response/RawViewer.tsx frontend/src/components/response/RawViewer.test.tsx
git commit -m "fix(frontend): drop redundant body panel from Raw response tab (F1)"
```

---

## F2 — Forget external workspace + stop fixtures polluting the real registry

### Task F2.1: `workspaces.forget_external`

**Files:**
- Modify: `drummer/core/storage/workspaces.py`
- Test: `tests/unit/test_workspaces.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_workspaces.py`:

```python
def test_forget_external_removes_registry_entry(drummer_home: Path, tmp_path: Path) -> None:
    external = tmp_path / "repo"
    external.mkdir()
    info = ws.register_external(external)
    ws.forget_external(info.id)
    externals = [w for w in ws.list_workspaces() if w.kind == "external"]
    assert externals == []


def test_forget_external_resets_active_to_scratch(drummer_home: Path, tmp_path: Path) -> None:
    external = tmp_path / "repo"
    external.mkdir()
    info = ws.register_external(external)
    ws.set_active(info.id)
    ws.forget_external(info.id)
    assert ws.get_active() == "scratch"


def test_forget_external_keeps_active_when_other_forgotten(
    drummer_home: Path, tmp_path: Path
) -> None:
    keep = tmp_path / "keep"
    keep.mkdir()
    drop = tmp_path / "drop"
    drop.mkdir()
    kept = ws.register_external(keep)
    dropped = ws.register_external(drop)
    ws.set_active(kept.id)
    ws.forget_external(dropped.id)
    assert ws.get_active() == kept.id


def test_forget_external_unknown_id_is_noop(drummer_home: Path, tmp_path: Path) -> None:
    ws.forget_external(str(tmp_path / "never-registered"))  # must not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/unit/test_workspaces.py -k forget -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'forget_external'`.

- [ ] **Step 3: Implement `forget_external`**

In `drummer/core/storage/workspaces.py`, add this function immediately after `register_external` (after line 144):

```python
def forget_external(workspace_id: str) -> None:
    resolved = str(Path(workspace_id).expanduser().resolve())
    registry = _read_registry()
    remaining = [entry for entry in registry if str(Path(entry).resolve()) != resolved]
    if remaining != registry:
        _write_registry(remaining)
    if get_active() == workspace_id:
        set_active("scratch")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/unit/test_workspaces.py -k forget -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add drummer/core/storage/workspaces.py tests/unit/test_workspaces.py
git commit -m "feat(core): forget_external removes a workspace from the registry (F2)"
```

---

### Task F2.2: `POST /api/workspaces/forget` route

**Files:**
- Modify: `drummer/api/routes/workspaces.py`
- Test: `tests/integration/test_workspaces_routes.py`

- [ ] **Step 1: Read the existing workspaces route test for fixture/style**

Run: `sed -n '1,40p' tests/integration/test_workspaces_routes.py`
Note the `client`/`project_dir` fixtures and how `DRUMMER_HOME` is isolated (the integration `conftest` does not set it; check whether this test file sets `DRUMMER_HOME` via monkeypatch — mirror whatever pattern the existing register/switch tests use).

- [ ] **Step 2: Write the failing test**

Append to `tests/integration/test_workspaces_routes.py` (mirror the existing tests' use of a `DRUMMER_HOME` temp override fixture; if the file uses a local `drummer_home`/`monkeypatch` fixture, add that fixture name to this test's signature exactly as the others do):

```python
async def test_forget_external_route(client: AsyncClient, tmp_path: Path) -> None:
    external = tmp_path / "ext-to-forget"
    external.mkdir()
    register = await client.post("/api/workspaces/register", json={"path": str(external)})
    assert register.status_code == HTTPStatus.OK
    ext_id = register.json()["id"]

    forget = await client.post("/api/workspaces/forget", json={"id": ext_id})
    assert forget.status_code == HTTPStatus.OK
    body = forget.json()
    assert all(w["id"] != ext_id for w in body["workspaces"])
    assert body["active"] == "scratch"
```

> If existing tests in this file isolate `DRUMMER_HOME` through a fixture, include that fixture in the signature so this test does not touch the real registry. Match the existing pattern exactly; do not invent a new one.

- [ ] **Step 3: Run test to verify it fails**

Run: `venv/bin/pytest tests/integration/test_workspaces_routes.py -k forget -v`
Expected: FAIL with 404 (route not registered).

- [ ] **Step 4: Implement the route**

In `drummer/api/routes/workspaces.py`, add a body model after `RegisterBody` (line 28):

```python
class ForgetBody(BaseModel):
    id: str
```

Then add this route after `register_workspace_route` (after line 45):

```python
@router.post("/workspaces/forget")
async def forget_workspace_route(body: ForgetBody, request: Request) -> WorkspaceListResponse:
    ws.forget_external(body.id)
    active = ws.get_active()
    request.app.state.project_dir = ws.resolve_workspace(active)
    return WorkspaceListResponse(workspaces=ws.list_workspaces(), active=active)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/bin/pytest tests/integration/test_workspaces_routes.py -k forget -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add drummer/api/routes/workspaces.py tests/integration/test_workspaces_routes.py
git commit -m "feat(api): POST /workspaces/forget to drop an external workspace (F2)"
```

---

### Task F2.3: `useForgetWorkspace` frontend hook

**Files:**
- Modify: `frontend/src/api/workspaces.ts`
- Test: `frontend/src/api/workspaces.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/api/workspaces.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "./client";
import { useForgetWorkspace } from "./workspaces";

vi.mock("./client", () => ({ apiFetch: vi.fn() }));

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useForgetWorkspace", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it("POSTs the workspace id to /api/workspaces/forget", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ workspaces: [], active: "scratch" });
    const { result } = renderHook(() => useForgetWorkspace(), { wrapper });
    await result.current.mutateAsync("/abs/path");
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));
    const [url, opts] = vi.mocked(apiFetch).mock.calls[0];
    expect(url).toBe("/api/workspaces/forget");
    expect(opts?.method).toBe("POST");
    expect(JSON.parse(opts?.body as string)).toEqual({ id: "/abs/path" });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/workspaces.test.tsx`
Expected: FAIL — `useForgetWorkspace` is not exported.

- [ ] **Step 3: Implement the hook**

In `frontend/src/api/workspaces.ts`, add after `useRegisterWorkspace` (after line 59), reusing the existing `WorkspaceListResponse` import:

```typescript
export function useForgetWorkspace() {
  const qc = useQueryClient();
  return useMutation<WorkspaceListResponse, Error, string>({
    mutationFn: (id) =>
      apiFetch<WorkspaceListResponse>("/api/workspaces/forget", {
        method: "POST",
        body: JSON.stringify({ id }),
      }),
    onSuccess: () => invalidateWorkspaceData(qc),
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/workspaces.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/workspaces.ts frontend/src/api/workspaces.test.tsx
git commit -m "feat(frontend): useForgetWorkspace mutation hook (F2)"
```

---

### Task F2.4: "Forget external workspace" action in the switcher

**Files:**
- Modify: `frontend/src/components/layout/WorkspaceSwitcher.tsx`
- Test: `frontend/src/components/layout/WorkspaceSwitcher.test.tsx`

- [ ] **Step 1: Update the test mock and add a render assertion**

In `frontend/src/components/layout/WorkspaceSwitcher.test.tsx`, add `useForgetWorkspace` to the mock object (inside the `vi.mock("../../api/workspaces", ...)` factory, alongside the other hooks):

```tsx
  useForgetWorkspace: () => ({ mutate: vi.fn() }),
```

Then add this test inside the `describe`:

```tsx
  it("does not offer Forget when the active workspace is not external", () => {
    render(<WorkspaceSwitcher />);
    expect(screen.queryByText(/Forget external workspace/)).not.toBeInTheDocument();
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/layout/WorkspaceSwitcher.test.tsx`
Expected: FAIL — the component does not yet import `useForgetWorkspace`, so the mock factory error surfaces (or the new assertion cannot resolve the component render). Confirm it is red before proceeding.

- [ ] **Step 3: Wire the Forget action**

In `frontend/src/components/layout/WorkspaceSwitcher.tsx`:

Add `useForgetWorkspace` to the import block (line 11-16):

```tsx
import {
  useCreateWorkspace,
  useForgetWorkspace,
  useRegisterWorkspace,
  useSwitchWorkspace,
  useWorkspaces,
} from "../../api/workspaces";
```

Add the sentinel constant after line 21 (`const ADD = "__add__";`):

```tsx
const FORGET = "__forget__";
```

Inside the component, after `const registerWorkspace = useRegisterWorkspace();` (line 27), add:

```tsx
  const forgetWorkspace = useForgetWorkspace();
```

After `const workspaces = data?.workspaces ?? [];` (line 32), add:

```tsx
  const activeIsExternal =
    workspaces.find((w) => w.id === active)?.kind === "external";
```

In `handleChange`, add a branch before the final `if (value !== active)` line (after the `ADD` branch closes at line 59):

```tsx
    if (value === FORGET) {
      if (window.confirm("Forget this external workspace? Files are not deleted.")) {
        forgetWorkspace.mutate(active);
      }
      return;
    }
```

In the rendered `<SelectContent>`, add the Forget item after the `ADD` item (after line 91), shown only when the active workspace is external:

```tsx
        {activeIsExternal && (
          <SelectItem value={FORGET}>✕ Forget external workspace…</SelectItem>
        )}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/layout/WorkspaceSwitcher.test.tsx`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/WorkspaceSwitcher.tsx frontend/src/components/layout/WorkspaceSwitcher.test.tsx
git commit -m "feat(frontend): Forget-external-workspace action in switcher (F2)"
```

> After this lands, the user can clear the stuck "Demo Project" entry: switch to it, then choose "✕ Forget external workspace…".

---

### Task F2.5: Isolate the e2e server's registry

**Files:**
- Modify: `tests/e2e/conftest.py`

- [ ] **Step 1: Understand the bug**

The `drummer_server` fixture spawns the real `drummer` binary against `tests/e2e/fixtures/demo-project`. `_launch` calls `workspaces.register_external`, which writes to `~/.drummer/registry.yaml` because `DRUMMER_HOME` is unset for the subprocess. That is how "Demo Project" permanently entered the real registry. Fix: give the subprocess an isolated `DRUMMER_HOME`.

- [ ] **Step 2: Apply the isolation**

In `tests/e2e/conftest.py`, change the `drummer_server` fixture to accept `tmp_path_factory` and pass an isolated `DRUMMER_HOME` in the subprocess environment. Replace the fixture definition (the `@pytest.fixture(scope="session", autouse=True)` block) with:

```python
@pytest.fixture(scope="session", autouse=True)
def drummer_server(tmp_path_factory: pytest.TempPathFactory):
    drummer_home = tmp_path_factory.mktemp("drummer-home")
    env = {**os.environ, "DRUMMER_HOME": str(drummer_home)}
    proc = subprocess.Popen(
        [str(_DRUMMER_BIN), "serve", "--project", str(FIXTURE_PROJECT), "--port", str(SERVER_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    try:
        _wait_for_server("127.0.0.1", SERVER_PORT, _STARTUP_TIMEOUT)
    except RuntimeError:
        proc.terminate()
        raise
    yield proc
    proc.terminate()
    proc.wait()
```

Add `import os` to the imports at the top of the file (alongside `import socket`).

- [ ] **Step 3: Verify the real registry is no longer touched**

Note the current real registry contents (it is fine if the file is absent):

Run: `cat ~/.drummer/registry.yaml 2>/dev/null || echo "(no registry file)"`

Then run the e2e suite (this builds the frontend and starts the server; it may take a minute):

Run: `make e2e`
Expected: e2e tests pass.

Run again: `cat ~/.drummer/registry.yaml 2>/dev/null || echo "(no registry file)"`
Expected: identical to the before-snapshot — the demo-project path is NOT added.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/conftest.py
git commit -m "test(e2e): isolate spawned server DRUMMER_HOME so fixtures don't pollute the real registry (F2)"
```

---

## Phase 15 — Request editing & CRUD

### Task 15.1 (CRITICAL): Backend — round-trip the full request on save

**Files:**
- Modify: `drummer/api/routes/requests.py`
- Test: `tests/integration/test_requests_routes.py`

- [ ] **Step 1: Rewrite the PUT test and add a preservation regression test**

In `tests/integration/test_requests_routes.py`, replace the existing `test_update_request` function (lines 34-60) with the two functions below. The new PUT contract is `PUT /api/requests/{path}` with body `{ "frontmatter": {...full RequestFrontmatter...}, "body": "..." }`, returning a full `RequestDetail`.

```python
async def test_update_request_full_roundtrip(client: AsyncClient) -> None:
    await client.post(
        "/api/requests",
        json={"path": "ping.md", "name": "Ping", "method": "GET", "url": "https://x.com"},
    )
    update_resp = await client.put(
        "/api/requests/ping.md",
        json={
            "frontmatter": {
                "name": "Ping Updated",
                "method": "POST",
                "url": "https://x.com/ping",
                "headers": {"Accept": "application/json"},
            },
            "body": "payload",
        },
    )
    assert update_resp.status_code == HTTPStatus.OK
    data = update_resp.json()
    # The PUT response must be a full RequestDetail, not a bare summary.
    assert data["frontmatter"]["name"] == "Ping Updated"
    assert data["frontmatter"]["method"] == "POST"
    assert data["body"] == "payload"

    get_resp = await client.get("/api/requests/ping.md")
    assert get_resp.json()["frontmatter"]["url"] == "https://x.com/ping"


async def test_update_request_preserves_auth_params_and_scripts(client: AsyncClient) -> None:
    # A request carrying auth, params, and a post-script.
    await client.post(
        "/api/requests",
        json={"path": "secure.md", "name": "Secure", "method": "GET", "url": "https://x.com"},
    )
    rich_frontmatter = {
        "name": "Secure",
        "method": "GET",
        "url": "https://x.com",
        "params": {"q": "search"},
        "auth": {"type": "bearer", "token": "secret-token"},
        "post_script": "dm.log('done')",
    }
    await client.put(
        "/api/requests/secure.md",
        json={"frontmatter": rich_frontmatter, "body": ""},
    )
    # Now save again changing ONLY the url, sending the full frontmatter back.
    changed = {**rich_frontmatter, "url": "https://x.com/v2"}
    await client.put("/api/requests/secure.md", json={"frontmatter": changed, "body": ""})

    fm = (await client.get("/api/requests/secure.md")).json()["frontmatter"]
    assert fm["url"] == "https://x.com/v2"
    assert fm["params"] == {"q": "search"}
    assert fm["auth"]["type"] == "bearer"
    assert fm["auth"]["token"] == "secret-token"
    assert fm["post_script"] == "dm.log('done')"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/integration/test_requests_routes.py -k "roundtrip or preserves" -v`
Expected: FAIL — the current PUT expects the old `CreateRequestBody` shape, so the `{frontmatter, body}` payload fails validation (422) / the response lacks `frontmatter`.

- [ ] **Step 3: Change the PUT contract**

In `drummer/api/routes/requests.py`, add a write-body model after `CreateRequestBody` (after line 37):

```python
class RequestWriteBody(BaseModel):
    frontmatter: RequestFrontmatter
    body: str = ""
```

Replace the entire `update_request_route` function (lines 85-94) with:

```python
@router.put("/requests/{path:path}")
async def update_request_route(
    path: str, body: RequestWriteBody, project_dir: ProjectDir
) -> RequestDetail:
    full_path = _safe_request_path(project_dir, path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Request not found: {path}")
    write_request_file(RequestFile(frontmatter=body.frontmatter, body=body.body, path=full_path))
    rf = parse_request_file(full_path)
    return RequestDetail(path=path, frontmatter=rf.frontmatter, body=rf.body)
```

(`RequestFrontmatter` and `parse_request_file` are already imported at the top of the file.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/integration/test_requests_routes.py -v`
Expected: PASS (all request-route tests, including the unchanged create/delete/list ones).

- [ ] **Step 5: Commit**

```bash
git add drummer/api/routes/requests.py tests/integration/test_requests_routes.py
git commit -m "fix(api): PUT /requests round-trips the full request, returns RequestDetail (15a/15b)"
```

---

### Task 15.2 (CRITICAL): Frontend — send the full frontmatter, accept RequestDetail back

**Files:**
- Modify: `frontend/src/api/requests.ts`
- Test: `frontend/src/api/requests.test.tsx` (create)

This fixes the white-screen crash: the old code sent only 5 fields and typed the `RequestSummary` response as `RequestDetail`, so `markSaved(result)` stored an object with no `frontmatter`, crashing the request pane on the next render.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/api/requests.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { RequestDetail } from "../types";
import { apiFetch } from "./client";
import { useSaveRequest } from "./requests";

vi.mock("./client", () => ({ apiFetch: vi.fn() }));

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function detail(): RequestDetail {
  return {
    path: "secure.md",
    body: "the body",
    frontmatter: {
      name: "Secure",
      method: "GET",
      url: "https://x.com",
      headers: {},
      params: { q: "search" },
      encoding: "utf-8",
      cookies: { mode: "session", cookies: {} },
      auth: {
        type: "bearer",
        token: "secret-token",
        username: "",
        password: "",
        key: "",
        value: "",
        token_url: "",
        client_id: "",
        client_secret: "",
        scope: "",
      },
      pre_script: "",
      post_script: "dm.log('x')",
      script_timeout_ms: null,
      tags: [],
      skip: false,
    },
  };
}

describe("useSaveRequest", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it("PUTs the full frontmatter and body (no field loss)", async () => {
    const d = detail();
    vi.mocked(apiFetch).mockResolvedValue(d);
    const { result } = renderHook(() => useSaveRequest(), { wrapper });
    await result.current.mutateAsync({ path: "secure.md", detail: d });
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));

    const [url, opts] = vi.mocked(apiFetch).mock.calls[0];
    expect(url).toBe("/api/requests/secure.md");
    expect(opts?.method).toBe("PUT");
    const sent = JSON.parse(opts?.body as string);
    expect(sent.frontmatter.params).toEqual({ q: "search" });
    expect(sent.frontmatter.auth.token).toBe("secret-token");
    expect(sent.frontmatter.post_script).toBe("dm.log('x')");
    expect(sent.body).toBe("the body");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/requests.test.tsx`
Expected: FAIL — current payload has no `frontmatter` key (it sends flat `name`/`method`/`url`/`headers`/`body`), so `sent.frontmatter` is `undefined`.

- [ ] **Step 3: Send the full frontmatter and type the response correctly**

In `frontend/src/api/requests.ts`, replace the `mutationFn` inside `useSaveRequest` (lines 28-39) with:

```typescript
    mutationFn: ({ path, detail }) =>
      apiFetch<RequestDetail>(`/api/requests/${path}`, {
        method: "PUT",
        body: JSON.stringify({
          frontmatter: detail.frontmatter,
          body: detail.body,
        }),
      }),
```

The mutation's declared result type is already `RequestDetail`, and the route now returns a real `RequestDetail`, so `onSuccess` / `markSaved(result)` receive a complete object.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/requests.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/requests.ts frontend/src/api/requests.test.tsx
git commit -m "fix(frontend): save sends full frontmatter and consumes RequestDetail (15a/15b)"
```

---

### Task 15.3: `deselect` store action

**Files:**
- Modify: `frontend/src/store/requestStore.ts`
- Test: `frontend/src/store/requestStore.test.ts` (create)

Needed so deleting the selected request clears the pane instead of leaving a dangling selection.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/store/requestStore.test.ts`:

```ts
import { beforeEach, describe, expect, it } from "vitest";
import { useRequestStore } from "./requestStore";

describe("requestStore.deselect", () => {
  beforeEach(() => {
    useRequestStore.setState({ selectedPath: null, saved: null, draft: null });
  });

  it("clears selection and loaded request", () => {
    useRequestStore.getState().select("foo.md");
    useRequestStore.getState().deselect();
    const s = useRequestStore.getState();
    expect(s.selectedPath).toBeNull();
    expect(s.saved).toBeNull();
    expect(s.draft).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/store/requestStore.test.ts`
Expected: FAIL — `deselect` is not a function.

- [ ] **Step 3: Add the action**

In `frontend/src/store/requestStore.ts`, add `deselect` to the `RequestState` interface (after `select` on line 9):

```ts
  deselect: () => void;
```

And add the implementation after the `select` implementation (after line 24):

```ts
  deselect: () => set({ selectedPath: null, saved: null, draft: null }),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/store/requestStore.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/requestStore.ts frontend/src/store/requestStore.test.ts
git commit -m "feat(frontend): requestStore.deselect to clear the active request (15d)"
```

---

### Task 15.4: `useCreateRequest` hook

**Files:**
- Modify: `frontend/src/api/requests.ts`
- Test: `frontend/src/api/requests.test.tsx`

- [ ] **Step 1: Write the failing test**

Append a new `describe` block to `frontend/src/api/requests.test.tsx` (the imports from Task 15.2 already cover what is needed except `useCreateRequest`):

```tsx
import { useCreateRequest } from "./requests";

describe("useCreateRequest", () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it("POSTs path and name to /api/requests", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      path: "new-request.md",
      name: "New Request",
      method: "GET",
      url: "",
    });
    const { result } = renderHook(() => useCreateRequest(), { wrapper });
    await result.current.mutateAsync({ path: "new-request.md", name: "New Request" });
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));
    const [url, opts] = vi.mocked(apiFetch).mock.calls[0];
    expect(url).toBe("/api/requests");
    expect(opts?.method).toBe("POST");
    expect(JSON.parse(opts?.body as string)).toMatchObject({
      path: "new-request.md",
      name: "New Request",
    });
  });
});
```

> Move the `import { useCreateRequest } from "./requests";` line up to join the existing `useSaveRequest` import (`import { useCreateRequest, useSaveRequest } from "./requests";`) so there is a single import statement; the inline form above is shown only to make the dependency explicit.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/requests.test.tsx`
Expected: FAIL — `useCreateRequest` is not exported.

- [ ] **Step 3: Implement the hook**

In `frontend/src/api/requests.ts`, add after `useRequest` (after line 19), reusing the existing `RequestSummary` import:

```typescript
export function useCreateRequest() {
  const queryClient = useQueryClient();
  return useMutation<RequestSummary, Error, { path: string; name: string }>({
    mutationFn: ({ path, name }) =>
      apiFetch<RequestSummary>("/api/requests", {
        method: "POST",
        body: JSON.stringify({ path, name }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["requests"] });
    },
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/requests.test.tsx`
Expected: PASS (both describe blocks).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/requests.ts frontend/src/api/requests.test.tsx
git commit -m "feat(frontend): useCreateRequest mutation hook (15d)"
```

---

### Task 15.5: Delete affordance on tree nodes

**Files:**
- Modify: `frontend/src/components/tree/TreeNode.tsx`
- Modify: `frontend/src/components/tree/RequestTree.tsx`
- Test: `frontend/src/components/tree/TreeNode.test.tsx` (create)

A `<button>` cannot be nested in a `<button>`, so the row is restructured into a wrapping `<div>` with a clickable row button plus a sibling delete button.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/tree/TreeNode.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { RequestSummary } from "../../types";
import { TreeNode } from "./TreeNode";

const request: RequestSummary = {
  path: "hello/get-hello.md",
  name: "Get Hello",
  method: "GET",
  url: "https://x.com",
};

describe("TreeNode", () => {
  it("calls onSelect when the row is clicked", () => {
    const onSelect = vi.fn();
    render(<TreeNode request={request} onSelect={onSelect} onDelete={vi.fn()} />);
    fireEvent.click(screen.getByText("Get Hello"));
    expect(onSelect).toHaveBeenCalledWith("hello/get-hello.md");
  });

  it("calls onDelete (and not onSelect) when delete is clicked", () => {
    const onSelect = vi.fn();
    const onDelete = vi.fn();
    render(<TreeNode request={request} onSelect={onSelect} onDelete={onDelete} />);
    fireEvent.click(screen.getByLabelText("Delete Get Hello"));
    expect(onDelete).toHaveBeenCalledWith("hello/get-hello.md");
    expect(onSelect).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/tree/TreeNode.test.tsx`
Expected: FAIL — `TreeNode` has no `onDelete` prop and no delete control.

- [ ] **Step 3: Restructure `TreeNode` with a delete button**

Replace the contents of `frontend/src/components/tree/TreeNode.tsx` (keep the existing `METHOD_COLOURS` map) with:

```tsx
import { useRequestStore } from "../../store/requestStore";
import type { RequestSummary } from "../../types";

const METHOD_COLOURS: Record<string, string> = {
  GET: "text-green-600 dark:text-green-400",
  POST: "text-blue-600 dark:text-blue-400",
  PUT: "text-amber-600 dark:text-amber-400",
  PATCH: "text-orange-500 dark:text-orange-400",
  DELETE: "text-red-600 dark:text-red-400",
  HEAD: "text-muted-foreground",
  OPTIONS: "text-muted-foreground",
  TRACE: "text-muted-foreground",
};

interface TreeNodeProps {
  request: RequestSummary;
  onSelect: (path: string) => void;
  onDelete: (path: string) => void;
}

export function TreeNode({ request, onSelect, onDelete }: TreeNodeProps) {
  const { selectedPath, isDirty } = useRequestStore();
  const isSelected = selectedPath === request.path;
  const dirty = isSelected && isDirty();

  return (
    <div
      className={`group flex w-full items-center rounded ${
        isSelected ? "bg-primary/10" : "hover:bg-muted"
      }`}
    >
      <button
        type="button"
        className={`flex flex-1 items-center gap-2 px-2 py-1 text-left text-sm ${
          isSelected ? "text-primary" : "text-foreground"
        }`}
        onClick={() => onSelect(request.path)}
        data-testid={`tree-node-${request.path}`}
      >
        <span
          className={`w-14 shrink-0 text-xs font-mono font-semibold ${METHOD_COLOURS[request.method] ?? "text-muted-foreground"}`}
        >
          {request.method}
        </span>
        <span className="flex-1 truncate">{request.name}</span>
        {dirty && (
          <span
            className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500"
            title="Unsaved changes"
          />
        )}
      </button>
      <button
        type="button"
        aria-label={`Delete ${request.name}`}
        className="px-1.5 text-xs text-muted-foreground opacity-0 hover:text-red-600 group-hover:opacity-100"
        onClick={() => onDelete(request.path)}
      >
        ✕
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Thread `onDelete` through `RequestTree`**

Replace the contents of `frontend/src/components/tree/RequestTree.tsx` with:

```tsx
import type { RequestSummary } from "../../types";
import { TreeNode } from "./TreeNode";

interface RequestTreeProps {
  requests: RequestSummary[];
  onSelect: (path: string) => void;
  onDelete: (path: string) => void;
}

export function RequestTree({ requests, onSelect, onDelete }: RequestTreeProps) {
  if (requests.length === 0) {
    return (
      <p className="px-2 py-4 text-xs text-muted-foreground">
        No requests found.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-0.5 py-1" data-testid="request-tree">
      {requests.map((r) => (
        <TreeNode
          key={r.path}
          request={r}
          onSelect={onSelect}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/tree/TreeNode.test.tsx`
Expected: PASS (2 tests). (`RequestTree` now requires `onDelete`; the Sidebar wiring in Task 15.6 supplies it — TypeScript may flag `Sidebar.tsx` until then, which the next task resolves.)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/tree/TreeNode.tsx frontend/src/components/tree/RequestTree.tsx frontend/src/components/tree/TreeNode.test.tsx
git commit -m "feat(frontend): per-request delete affordance in the tree (15d)"
```

---

### Task 15.6: Sidebar — "+ New request" button and delete wiring

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Add props and the new-request button**

Replace the contents of `frontend/src/components/layout/Sidebar.tsx` with:

```tsx
import { useEnvironments } from "../../api/environments";
import { useProjectStore } from "../../store/projectStore";
import { useSessionStore } from "../../store/sessionStore";
import { RequestTree } from "../tree/RequestTree";

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

      {environments.length > 0 && (
        <div className="border-b px-3 py-2">
          <label
            htmlFor="environment-select"
            className="text-xs text-muted-foreground"
          >
            Environment
          </label>
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
        </div>
      )}

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
    </div>
  );
}
```

- [ ] **Step 2: Verify the frontend type-checks (no test for layout shell)**

Run: `cd frontend && npx tsc --noEmit`
Expected: `WorkspaceView.tsx` errors (Sidebar now requires `onRequestDelete`/`onNewRequest`) — those are resolved in Task 15.7. No errors inside `Sidebar.tsx` itself.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/Sidebar.tsx
git commit -m "feat(frontend): New-request button and delete wiring in Sidebar (15d)"
```

---

### Task 15.7: WorkspaceView — wire create, delete, and save handlers

**Files:**
- Modify: `frontend/src/views/WorkspaceView.tsx`

- [ ] **Step 1: Add the handlers and a Save prop for the workbench**

In `frontend/src/views/WorkspaceView.tsx`:

Update the requests-api import (line 2) to include the new hooks:

```tsx
import {
  useCreateRequest,
  useDeleteRequest,
  useRequest,
  useRequests,
  useSaveRequest,
} from "../api/requests";
```

Add the `deselect` selector after `isDirty` (after line 23):

```tsx
  const deselect = useRequestStore((s) => s.deselect);
```

Add the mutation hooks after `const saveRequest = useSaveRequest();` (after line 29):

```tsx
  const createRequest = useCreateRequest();
  const deleteRequest = useDeleteRequest();
```

Add these handlers after `handleSend` (after line 55):

```tsx
  const handleNewRequest = useCallback(async () => {
    const name = window.prompt("New request name:")?.trim();
    if (!name) return;
    const slug =
      name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/(^-|-$)/g, "") || "request";
    const path = `${slug}.md`;
    await createRequest.mutateAsync({ path, name });
    handleRequestSelect(path);
  }, [createRequest, handleRequestSelect]);

  const handleRequestDelete = useCallback(
    async (path: string) => {
      if (!window.confirm("Delete this request? This cannot be undone.")) return;
      await deleteRequest.mutateAsync(path);
      if (selectedPath === path) deselect();
    },
    [deleteRequest, selectedPath, deselect],
  );
```

Pass `onSave` to the workbench and the new handlers to the sidebar. Replace the `sidebar` and `mainArea` declarations (lines 85-89) with:

```tsx
  const sidebar = (
    <Sidebar
      onRequestSelect={handleRequestSelect}
      onRequestDelete={handleRequestDelete}
      onNewRequest={handleNewRequest}
    />
  );

  const mainArea = (
    <RequestResponseWorkbench
      onSend={handleSend}
      onCancel={cancel}
      onSave={handleSave}
    />
  );
```

- [ ] **Step 2: Verify type-check (workbench prop lands in Task 15.8)**

Run: `cd frontend && npx tsc --noEmit`
Expected: one remaining error — `RequestResponseWorkbench` does not yet accept `onSave`. Resolved in Task 15.8.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/WorkspaceView.tsx
git commit -m "feat(frontend): wire new/delete request handlers and save into WorkspaceView (15c/15d)"
```

---

### Task 15.8: Visible Save button in the URL bar

**Files:**
- Modify: `frontend/src/components/layout/RequestResponseWorkbench.tsx`
- Modify: `frontend/src/components/request/UrlBar.tsx`

- [ ] **Step 1: Accept `onSave` in the workbench and compute dirty**

In `frontend/src/components/layout/RequestResponseWorkbench.tsx`:

Extend the props interface (lines 37-40):

```tsx
interface RequestResponseWorkbenchProps {
  onSend: () => void;
  onCancel: () => void;
  onSave: () => void;
}
```

Update the component signature (lines 42-45):

```tsx
export function RequestResponseWorkbench({
  onSend,
  onCancel,
  onSave,
}: RequestResponseWorkbenchProps) {
```

The component already selects `saved` and `draft` (lines 46-47). After `const current = draft ?? saved;` (line 62), add:

```tsx
  const canSave = draft !== null && JSON.stringify(draft) !== JSON.stringify(saved);
```

Pass the two new props into `<UrlBar .../>` (add to the existing prop list at lines 69-78):

```tsx
        onSave={onSave}
        canSave={canSave}
```

- [ ] **Step 2: Add the Save button to `UrlBar`**

In `frontend/src/components/request/UrlBar.tsx`:

Extend `UrlBarProps` (lines 30-39) with:

```tsx
  onSave: () => void;
  canSave: boolean;
```

Add `onSave` and `canSave` to the destructured params (lines 41-50):

```tsx
  onSave,
  canSave,
```

Add a Save button just before the `isStreaming ? ... : ...` Send/Cancel block (before line 156). It sits to the left of Send:

```tsx
      <button
        type="button"
        className="rounded border px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
        onClick={onSave}
        disabled={!canSave}
        data-testid="save-button"
      >
        Save
      </button>
```

- [ ] **Step 3: Verify the whole frontend type-checks and tests pass**

Run: `cd frontend && npm run check`
Expected: Biome clean, `tsc --noEmit` clean (no remaining `onSave` errors).

Run: `cd frontend && npx vitest run`
Expected: all frontend tests pass.

- [ ] **Step 4: Manual verification in the running app**

Run the app and confirm the save UX end to end (this is the behaviour the automated tests cannot fully cover because `UrlBar` embeds CodeMirror):

```bash
make dev
```

Then in the browser (Vite on http://localhost:5173):
1. Select the hello request, change the URL — the Save button enables and the dirty dot appears.
2. Click **Save** (and separately test cmd-s) — the dirty dot clears, the UI does **not** blank out.
3. Add an Auth bearer token and a post-script, Save, reload the page — token and script are still present (no data loss).
4. Click **+ New**, name it, confirm it appears and is selected.
5. Hover a request, click **✕**, confirm it deletes and the pane clears if it was selected.

Stop the dev servers when done (Ctrl-C).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/RequestResponseWorkbench.tsx frontend/src/components/request/UrlBar.tsx
git commit -m "feat(frontend): visible Save button in the URL bar (15c)"
```

---

### Task 15.9: Full-suite gate

**Files:** none (verification only)

- [ ] **Step 1: Run the complete check**

Run: `make check`
Expected: ruff clean, pyright 0 errors, Biome clean, `tsc` clean, all Python unit + integration tests pass, all frontend tests pass.

- [ ] **Step 2: Fix anything red at the root (no suppression comments), then re-run `make check`.**

- [ ] **Step 3: Update project docs**

Update `TODO.md` to reflect that F1, F2, and Phase 15 are done, and add a one-line note in the appropriate place (e.g., `ROADMAP.md`) that file-rename/move + folders remain deferred to a future phase. Commit:

```bash
git add TODO.md ROADMAP.md
git commit -m "docs: mark F1/F2/Phase 15 complete; note rename/move deferral"
```

---

## Self-Review

- **Spec coverage:**
  - F1 (raw tab) → Task F1. ✓
  - F2 (forget external + stop fixture pollution) → Tasks F2.1–F2.5. ✓
  - 15a (no data loss on save) → Task 15.1 (`test_update_request_preserves_*`) + 15.2. ✓
  - 15b (no blank-screen crash; PUT returns full detail) → Task 15.1 (returns `RequestDetail`) + 15.2 (typed result feeds `markSaved`). ✓
  - 15c (visible Save affordance) → Tasks 15.7–15.8. ✓
  - 15d (new + delete requests) → Tasks 15.3–15.7. Rename/move explicitly deferred (documented). ✓
- **Placeholder scan:** No TBD/TODO/"handle edge cases"; every code step has complete code. ✓
- **Type consistency:** PUT body is `RequestWriteBody { frontmatter, body }` in both the route (15.1) and the frontend payload (15.2); the save mutation result and the route return type are both `RequestDetail`. `useCreateRequest` arg `{ path, name }` matches the route's `CreateRequestBody` (extra fields tolerated by Pydantic). `TreeNode`/`RequestTree`/`Sidebar`/`WorkspaceView` all pass `onDelete`/`onRequestDelete`/`onNewRequest`/`onSave` with matching signatures. `forget_external(workspace_id: str)` matches the route's `body.id` and the hook's `mutateAsync(id)`. ✓
