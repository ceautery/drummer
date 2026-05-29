# Phase 11 — Workspaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pivot Drummer from a single startup-bound project to a workspaces model: central `~/.drummer/` storage with a special "Scratch" catchall, registered external folders, bare `drummer` launching the server, and a top-bar workspace switcher for cycling workspaces mid-session.

**Architecture:** A new pure-Python `core/storage/workspaces.py` owns all storage logic (discovery, registry, active-workspace config), isolated for testing via a `DRUMMER_HOME` env override. A FastAPI `workspaces` router exposes list/switch/create/register and updates the existing `app.state.project_dir` pointer — so every other route is untouched. The CLI's top-level callback launches the server (with `serve` kept as a hidden alias). The frontend gains a persistent `AppBar` hosting a `WorkspaceSwitcher`; the old `WelcomeView` is deleted.

**Tech Stack:** Python 3.12, Typer, FastAPI, Pydantic, PyYAML, pytest; React + Vite, Zustand, TanStack Query, base-ui Select, Vitest + Testing Library.

---

## File Structure

**Backend**
- Create: `drummer/core/storage/workspaces.py` — all workspace storage logic
- Create: `drummer/api/routes/workspaces.py` — list/switch/create/register routes
- Modify: `drummer/api/app.py` — include the new router
- Modify: `drummer/cli.py` — bare `drummer` launches; `serve` hidden alias; `new` de-stubbed; `--project` registers external
- Create: `tests/unit/test_workspaces.py`
- Create: `tests/integration/test_workspaces_routes.py`
- Modify: `tests/unit/test_cli.py`

**Frontend**
- Modify: `frontend/src/types.ts` — `WorkspaceInfo`, `WorkspaceListResponse`
- Create: `frontend/src/api/workspaces.ts`
- Create: `frontend/src/components/layout/WorkspaceSwitcher.tsx`
- Create: `frontend/src/components/layout/WorkspaceSwitcher.test.tsx`
- Create: `frontend/src/components/layout/AppBar.tsx`
- Modify: `frontend/src/App.tsx` — render AppBar + WorkspaceView, drop WelcomeView
- Modify: `frontend/src/views/WorkspaceView.tsx` — root `h-screen` → `h-full`
- Delete: `frontend/src/views/WelcomeView.tsx`

**Docs**
- Modify: `ROADMAP.md`, `CLAUDE.md`, `README.md`

---

## Task 1: Workspaces core — paths, model, scratch bootstrap, slugify

**Files:**
- Create: `drummer/core/storage/workspaces.py`
- Test: `tests/unit/test_workspaces.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_workspaces.py
import os
from pathlib import Path

import pytest

from drummer.core.storage import workspaces as ws


@pytest.fixture
def drummer_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("DRUMMER_HOME", str(tmp_path))
    return tmp_path


def test_home_respects_env_override(drummer_home: Path) -> None:
    assert ws.home() == drummer_home


def test_home_defaults_to_dot_drummer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DRUMMER_HOME", raising=False)
    assert ws.home() == Path.home() / ".drummer"


def test_ensure_scratch_creates_special_workspace(drummer_home: Path) -> None:
    ws.ensure_scratch()
    cfg = drummer_home / "projects" / "scratch" / ".drummer" / "project.yaml"
    assert cfg.exists()


def test_ensure_scratch_is_idempotent(drummer_home: Path) -> None:
    ws.ensure_scratch()
    ws.ensure_scratch()
    assert (drummer_home / "projects" / "scratch" / ".drummer" / "project.yaml").exists()


@pytest.mark.parametrize(
    "name,expected",
    [("My API", "my-api"), ("acme_API!!", "acme-api"), ("   ", "workspace")],
)
def test_slugify(name: str, expected: str) -> None:
    assert ws.slugify(name) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/unit/test_workspaces.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'drummer.core.storage.workspaces'`

- [ ] **Step 3: Write minimal implementation**

```python
# drummer/core/storage/workspaces.py
import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from drummer.core.storage.project import create_project, load_project


class WorkspaceInfo(BaseModel):
    id: str  # central slug, or absolute path for external workspaces
    name: str
    kind: Literal["central", "external"]
    path: str
    is_scratch: bool


def home() -> Path:
    override = os.environ.get("DRUMMER_HOME")
    return Path(override) if override else Path.home() / ".drummer"


def _projects_dir() -> Path:
    return home() / "projects"


def _config_path() -> Path:
    return home() / "config.yaml"


def _registry_path() -> Path:
    return home() / "registry.yaml"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "workspace"


def ensure_scratch() -> None:
    scratch = _projects_dir() / "scratch"
    if not (scratch / ".drummer" / "project.yaml").exists():
        scratch.mkdir(parents=True, exist_ok=True)
        create_project(scratch, "Scratch")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/pytest tests/unit/test_workspaces.py -q`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add drummer/core/storage/workspaces.py tests/unit/test_workspaces.py
git commit -m "feat(core): workspaces module — paths, scratch bootstrap, slugify"
```

---

## Task 2: Workspaces core — list, create, register, resolve, active

**Files:**
- Modify: `drummer/core/storage/workspaces.py`
- Test: `tests/unit/test_workspaces.py`

- [ ] **Step 1: Write the failing test (append to the file)**

```python
def test_list_workspaces_scratch_first(drummer_home: Path) -> None:
    ws.create_workspace("Zebra API")
    ws.create_workspace("Alpha API")
    result = ws.list_workspaces()
    assert result[0].is_scratch is True
    assert result[0].id == "scratch"
    assert [w.name for w in result[1:]] == ["Alpha API", "Zebra API"]


def test_create_workspace_central(drummer_home: Path) -> None:
    info = ws.create_workspace("My API")
    assert info.id == "my-api"
    assert info.kind == "central"
    assert info.is_scratch is False
    assert (Path(info.path) / ".drummer" / "project.yaml").exists()


def test_create_workspace_rejects_duplicate(drummer_home: Path) -> None:
    ws.create_workspace("My API")
    with pytest.raises(ValueError):
        ws.create_workspace("my api")


def test_register_external_initializes_and_lists(drummer_home: Path, tmp_path: Path) -> None:
    external = tmp_path / "outside-repo"
    external.mkdir()
    info = ws.register_external(external)
    assert info.kind == "external"
    assert info.id == str(external.resolve())
    assert (external / ".drummer" / "project.yaml").exists()
    ids = [w.id for w in ws.list_workspaces()]
    assert str(external.resolve()) in ids


def test_register_external_is_deduped(drummer_home: Path, tmp_path: Path) -> None:
    external = tmp_path / "repo"
    external.mkdir()
    ws.register_external(external)
    ws.register_external(external)
    externals = [w for w in ws.list_workspaces() if w.kind == "external"]
    assert len(externals) == 1


def test_get_active_defaults_to_scratch(drummer_home: Path) -> None:
    assert ws.get_active() == "scratch"


def test_set_and_get_active(drummer_home: Path) -> None:
    ws.create_workspace("My API")
    ws.set_active("my-api")
    assert ws.get_active() == "my-api"


def test_get_active_falls_back_when_missing(drummer_home: Path) -> None:
    ws.set_active("does-not-exist")
    assert ws.get_active() == "scratch"


def test_resolve_workspace_central_vs_external(drummer_home: Path, tmp_path: Path) -> None:
    assert ws.resolve_workspace("scratch") == _projects(drummer_home) / "scratch"
    ext = tmp_path / "ext"
    assert ws.resolve_workspace(str(ext)) == ext


def _projects(home_dir: Path) -> Path:
    return home_dir / "projects"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/unit/test_workspaces.py -q`
Expected: FAIL — `AttributeError: module 'drummer.core.storage.workspaces' has no attribute 'list_workspaces'`

- [ ] **Step 3: Write minimal implementation (append to `workspaces.py`)**

```python
def _read_registry() -> list[str]:
    path = _registry_path()
    if not path.exists():
        return []
    data: dict[str, object] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    external = data.get("external", [])
    return [str(p) for p in external] if isinstance(external, list) else []


def _write_registry(external: list[str]) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump({"external": external}, default_flow_style=False), encoding="utf-8")


def _central_workspaces() -> list[WorkspaceInfo]:
    result: list[WorkspaceInfo] = []
    pdir = _projects_dir()
    if not pdir.exists():
        return result
    for child in sorted(pdir.iterdir()):
        if not (child / ".drummer" / "project.yaml").exists():
            continue
        meta = load_project(child)
        result.append(
            WorkspaceInfo(
                id=child.name,
                name=meta.name,
                kind="central",
                path=str(child.resolve()),
                is_scratch=child.name == "scratch",
            )
        )
    return result


def _external_workspaces() -> list[WorkspaceInfo]:
    result: list[WorkspaceInfo] = []
    for raw in _read_registry():
        path = Path(raw)
        if not (path / ".drummer" / "project.yaml").exists():
            continue
        meta = load_project(path)
        result.append(
            WorkspaceInfo(
                id=str(path.resolve()),
                name=meta.name,
                kind="external",
                path=str(path.resolve()),
                is_scratch=False,
            )
        )
    return result


def list_workspaces() -> list[WorkspaceInfo]:
    ensure_scratch()
    central = _central_workspaces()
    scratch = [w for w in central if w.is_scratch]
    others = sorted((w for w in central if not w.is_scratch), key=lambda w: w.name.lower())
    return scratch + others + _external_workspaces()


def create_workspace(name: str) -> WorkspaceInfo:
    slug = slugify(name)
    target = _projects_dir() / slug
    if (target / ".drummer" / "project.yaml").exists():
        raise ValueError(f"Workspace '{slug}' already exists")
    target.mkdir(parents=True, exist_ok=True)
    create_project(target, name)
    return WorkspaceInfo(
        id=slug, name=name, kind="central", path=str(target.resolve()), is_scratch=False
    )


def register_external(path: Path) -> WorkspaceInfo:
    resolved = path.expanduser().resolve()
    if not (resolved / ".drummer" / "project.yaml").exists():
        resolved.mkdir(parents=True, exist_ok=True)
        create_project(resolved, resolved.name)
    registry = _read_registry()
    if str(resolved) not in registry:
        registry.append(str(resolved))
        _write_registry(registry)
    meta = load_project(resolved)
    return WorkspaceInfo(
        id=str(resolved), name=meta.name, kind="external", path=str(resolved), is_scratch=False
    )


def resolve_workspace(workspace_id: str) -> Path:
    candidate = Path(workspace_id)
    return candidate if candidate.is_absolute() else _projects_dir() / workspace_id


def _workspace_exists(workspace_id: str) -> bool:
    return (resolve_workspace(workspace_id) / ".drummer" / "project.yaml").exists()


def get_active() -> str:
    path = _config_path()
    if path.exists():
        data: dict[str, object] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        active = data.get("active_workspace")
        if isinstance(active, str) and _workspace_exists(active):
            return active
    return "scratch"


def set_active(workspace_id: str) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, object] = {}
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data["active_workspace"] = workspace_id
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def active_workspace_dir() -> Path:
    ensure_scratch()
    return resolve_workspace(get_active())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/pytest tests/unit/test_workspaces.py -q`
Expected: PASS (all tests)

- [ ] **Step 5: Run full backend gate**

Run: `venv/bin/ruff check . && venv/bin/pyright drummer && venv/bin/pytest tests/unit -q`
Expected: PASS, 0 pyright errors

- [ ] **Step 6: Commit**

```bash
git add drummer/core/storage/workspaces.py tests/unit/test_workspaces.py
git commit -m "feat(core): workspaces list/create/register/resolve/active"
```

---

## Task 3: Workspaces API router

**Files:**
- Create: `drummer/api/routes/workspaces.py`
- Modify: `drummer/api/app.py` (import + include router near the other `app.include_router(...)` calls)
- Test: `tests/integration/test_workspaces_routes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_workspaces_routes.py
from collections.abc import AsyncGenerator
from http import HTTPStatus
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.api.db.session import init_db
from drummer.core.storage import workspaces as ws


@pytest_asyncio.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setenv("DRUMMER_HOME", str(tmp_path / "home"))
    ws.ensure_scratch()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    application = create_app(project_dir=ws.active_workspace_dir(), db_url=db_url)
    await init_db(db_url)
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
        yield ac


async def test_list_returns_scratch_active(client: AsyncClient) -> None:
    r = await client.get("/api/workspaces")
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert data["active"] == "scratch"
    assert data["workspaces"][0]["is_scratch"] is True


async def test_create_workspace(client: AsyncClient) -> None:
    r = await client.post("/api/workspaces", json={"name": "My API"})
    assert r.status_code == HTTPStatus.OK
    assert r.json()["id"] == "my-api"


async def test_create_duplicate_conflicts(client: AsyncClient) -> None:
    await client.post("/api/workspaces", json={"name": "My API"})
    r = await client.post("/api/workspaces", json={"name": "my api"})
    assert r.status_code == HTTPStatus.CONFLICT


async def test_switch_active(client: AsyncClient) -> None:
    await client.post("/api/workspaces", json={"name": "My API"})
    r = await client.post("/api/workspaces/active", json={"id": "my-api"})
    assert r.status_code == HTTPStatus.OK
    assert r.json()["id"] == "my-api"
    assert (await client.get("/api/workspaces")).json()["active"] == "my-api"


async def test_switch_unknown_404(client: AsyncClient) -> None:
    r = await client.post("/api/workspaces/active", json={"id": "ghost"})
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_register_external(client: AsyncClient, tmp_path: Path) -> None:
    external = tmp_path / "ext-repo"
    external.mkdir()
    r = await client.post("/api/workspaces/register", json={"path": str(external)})
    assert r.status_code == HTTPStatus.OK
    assert r.json()["kind"] == "external"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/integration/test_workspaces_routes.py -q`
Expected: FAIL — 404s on `/api/workspaces` (router not mounted)

- [ ] **Step 3: Write the router**

```python
# drummer/api/routes/workspaces.py
from http import HTTPStatus
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from drummer.core.storage import workspaces as ws

router = APIRouter()


class WorkspaceListResponse(BaseModel):
    workspaces: list[ws.WorkspaceInfo]
    active: str


class SwitchBody(BaseModel):
    id: str


class CreateBody(BaseModel):
    name: str


class RegisterBody(BaseModel):
    path: str


@router.get("/workspaces")
async def list_workspaces_route() -> WorkspaceListResponse:
    return WorkspaceListResponse(workspaces=ws.list_workspaces(), active=ws.get_active())


@router.post("/workspaces")
async def create_workspace_route(body: CreateBody) -> ws.WorkspaceInfo:
    try:
        return ws.create_workspace(body.name)
    except ValueError as exc:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(exc)) from exc


@router.post("/workspaces/register")
async def register_workspace_route(body: RegisterBody) -> ws.WorkspaceInfo:
    return ws.register_external(Path(body.path))


@router.post("/workspaces/active")
async def switch_workspace_route(body: SwitchBody, request: Request) -> ws.WorkspaceInfo:
    target = ws.resolve_workspace(body.id)
    if not (target / ".drummer" / "project.yaml").exists():
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Workspace not found")
    ws.set_active(body.id)
    request.app.state.project_dir = target
    for info in ws.list_workspaces():
        if info.id == body.id:
            return info
    return ws.WorkspaceInfo(
        id=body.id, name=target.name, kind="central", path=str(target), is_scratch=False
    )
```

- [ ] **Step 4: Mount the router in `drummer/api/app.py`**

Add to the imports block alongside the other route imports:

```python
from drummer.api.routes import workspaces as workspace_routes
```

Add alongside the other `app.include_router(...)` calls (after the `project_routes` line):

```python
    app.include_router(workspace_routes.router, prefix="/api")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/bin/pytest tests/integration/test_workspaces_routes.py -q`
Expected: PASS (6 tests)

- [ ] **Step 6: Run full backend gate**

Run: `venv/bin/ruff check . && venv/bin/pyright drummer && venv/bin/pytest tests/unit tests/integration -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add drummer/api/routes/workspaces.py drummer/api/app.py tests/integration/test_workspaces_routes.py
git commit -m "feat(api): workspaces router (list/switch/create/register)"
```

---

## Task 4: CLI pivot — bare `drummer` launches, `serve` hidden alias, `new` de-stubbed

**Files:**
- Modify: `drummer/cli.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write/adjust the failing tests**

Add these to `tests/unit/test_cli.py` (keep existing tests; `test_serve_command_exists` and `test_new_command_exists` still pass because `serve` and `new` still exist):

```python
def test_bare_drummer_launches_server(monkeypatch, tmp_path):
    monkeypatch.setenv("DRUMMER_HOME", str(tmp_path))
    calls = {}

    def fake_run(application, host, port):
        calls["host"] = host
        calls["port"] = port

    monkeypatch.setattr("drummer.cli.uvicorn.run", fake_run)
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert calls["port"] == 8000


def test_new_creates_central_workspace(monkeypatch, tmp_path):
    monkeypatch.setenv("DRUMMER_HOME", str(tmp_path))
    result = runner.invoke(app, ["new", "My API"])
    assert result.exit_code == 0
    assert (tmp_path / "projects" / "my-api" / ".drummer" / "project.yaml").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/unit/test_cli.py -q`
Expected: FAIL — bare invoke prints help (exits before launch); `new` is still a stub that does not create files

- [ ] **Step 3: Rewrite `drummer/cli.py`**

```python
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from drummer import __version__
from drummer.api.app import create_app
from drummer.core.storage import workspaces
from drummer.core.storage.project import load_project

_ATTRIBUTION = (
    "Drummer includes data from the Metropolitan Museum of Art Open Access collection.\n"
    "License: Creative Commons Zero (CC0)\n"
    "Source: https://www.metmuseum.org/about-the-met/policies-and-documents/open-access\n"
    "The Met makes its Open Access data available for unrestricted use."
)

app = typer.Typer(name="drummer", help="Drummer — a local REST client.")

ProjectOpt = Annotated[
    str | None, typer.Option("--project", "-p", help="Open an external project folder.")
]
PortOpt = Annotated[int, typer.Option("--port", help="Port to listen on.")]
HostOpt = Annotated[str, typer.Option("--host", help="Host address to bind to.")]


def _launch(project: str | None, port: int, host: str) -> None:
    workspaces.ensure_scratch()
    if project is not None:
        info = workspaces.register_external(Path(project))
        workspaces.set_active(info.id)
        project_dir = Path(info.path)
    else:
        project_dir = workspaces.active_workspace_dir()
    application = create_app(project_dir=project_dir)
    meta = load_project(project_dir)
    typer.echo(f"Drummer serving '{meta.name}' on http://{host}:{port}")
    uvicorn.run(application, host=host, port=port)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    attribution: Annotated[
        bool, typer.Option("--attribution", help="Print dataset credits and exit.")
    ] = False,
    version: Annotated[
        bool, typer.Option("--version", "-V", help="Print version and exit.")
    ] = False,
    project: ProjectOpt = None,
    port: PortOpt = 8000,
    host: HostOpt = "127.0.0.1",
) -> None:
    if attribution:
        typer.echo(_ATTRIBUTION)
        raise typer.Exit()
    if version:
        typer.echo(f"Drummer {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        _launch(project, port, host)


@app.command(hidden=True)
def serve(project: ProjectOpt = None, port: PortOpt = 8000, host: HostOpt = "127.0.0.1") -> None:
    """Start the Drummer API server (alias for the bare `drummer` command)."""
    _launch(project, port, host)


@app.command()
def new(name: Annotated[str, typer.Argument(help="Name for the new workspace.")]) -> None:
    """Create a new central workspace under ~/.drummer/projects/."""
    info = workspaces.create_workspace(name)
    typer.echo(f"Created workspace '{info.name}' at {info.path}")


@app.command()
def export(path: Annotated[str, typer.Argument(help="Path of the project to export.")]) -> None:
    """Export a Drummer project at PATH as a zip file."""
    typer.echo(f"Exporting project at {path} ...")
    typer.echo("(Not yet implemented)")


@app.command()
def mcp() -> None:
    """Print MCP server connection info."""
    typer.echo("MCP server info: not yet implemented — Phase 4")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/unit/test_cli.py -q`
Expected: PASS (existing + 2 new tests)

- [ ] **Step 5: Run full backend gate**

Run: `venv/bin/ruff check . && venv/bin/pyright drummer && venv/bin/pytest tests/unit tests/integration -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add drummer/cli.py tests/unit/test_cli.py
git commit -m "feat(cli): bare drummer launches server; new creates central workspace"
```

---

## Task 5: Frontend — types + workspaces API client

**Files:**
- Modify: `frontend/src/types.ts`
- Create: `frontend/src/api/workspaces.ts`

- [ ] **Step 1: Add types to `frontend/src/types.ts`**

```ts
export interface WorkspaceInfo {
  id: string;
  name: string;
  kind: "central" | "external";
  path: string;
  is_scratch: boolean;
}

export interface WorkspaceListResponse {
  workspaces: WorkspaceInfo[];
  active: string;
}
```

- [ ] **Step 2: Create `frontend/src/api/workspaces.ts`**

```ts
import {
  type QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { WorkspaceInfo, WorkspaceListResponse } from "../types";
import { apiFetch } from "./client";

export function useWorkspaces() {
  return useQuery<WorkspaceListResponse>({
    queryKey: ["workspaces"],
    queryFn: () => apiFetch<WorkspaceListResponse>("/api/workspaces"),
  });
}

function invalidateWorkspaceData(qc: QueryClient) {
  void qc.invalidateQueries({ queryKey: ["workspaces"] });
  void qc.invalidateQueries({ queryKey: ["project"] });
  void qc.invalidateQueries({ queryKey: ["requests"] });
  void qc.invalidateQueries({ queryKey: ["environments"] });
  void qc.invalidateQueries({ queryKey: ["history"] });
}

export function useSwitchWorkspace() {
  const qc = useQueryClient();
  return useMutation<WorkspaceInfo, Error, string>({
    mutationFn: (id) =>
      apiFetch<WorkspaceInfo>("/api/workspaces/active", {
        method: "POST",
        body: JSON.stringify({ id }),
      }),
    onSuccess: () => invalidateWorkspaceData(qc),
  });
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation<WorkspaceInfo, Error, string>({
    mutationFn: (name) =>
      apiFetch<WorkspaceInfo>("/api/workspaces", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => invalidateWorkspaceData(qc),
  });
}

export function useRegisterWorkspace() {
  const qc = useQueryClient();
  return useMutation<WorkspaceInfo, Error, string>({
    mutationFn: (path) =>
      apiFetch<WorkspaceInfo>("/api/workspaces/register", {
        method: "POST",
        body: JSON.stringify({ path }),
      }),
    onSuccess: () => invalidateWorkspaceData(qc),
  });
}
```

- [ ] **Step 3: Verify it type-checks**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/workspaces.ts
git commit -m "feat(frontend): workspace types and API client"
```

---

## Task 6: Frontend — WorkspaceSwitcher component

**Files:**
- Create: `frontend/src/components/layout/WorkspaceSwitcher.tsx`
- Create: `frontend/src/components/layout/WorkspaceSwitcher.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/layout/WorkspaceSwitcher.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

vi.mock("../../api/workspaces", () => ({
  useWorkspaces: () => ({
    data: {
      active: "scratch",
      workspaces: [
        { id: "scratch", name: "Scratch", kind: "central", path: "/s", is_scratch: true },
        { id: "my-api", name: "My API", kind: "central", path: "/m", is_scratch: false },
      ],
    },
  }),
  useSwitchWorkspace: () => ({ mutate: vi.fn() }),
  useCreateWorkspace: () => ({ mutate: vi.fn() }),
  useRegisterWorkspace: () => ({ mutate: vi.fn() }),
}));

describe("WorkspaceSwitcher", () => {
  it("shows the active workspace in the trigger", () => {
    render(<WorkspaceSwitcher />);
    expect(screen.getByText(/Scratch/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/layout/WorkspaceSwitcher.test.tsx`
Expected: FAIL — cannot resolve `./WorkspaceSwitcher`

- [ ] **Step 3: Write the component**

```tsx
// frontend/src/components/layout/WorkspaceSwitcher.tsx
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreateWorkspace,
  useRegisterWorkspace,
  useSwitchWorkspace,
  useWorkspaces,
} from "../../api/workspaces";
import type { WorkspaceInfo } from "../../types";
import { useRequestStore } from "../../store/requestStore";

const NEW = "__new__";
const ADD = "__add__";

export function WorkspaceSwitcher() {
  const { data } = useWorkspaces();
  const switchWorkspace = useSwitchWorkspace();
  const createWorkspace = useCreateWorkspace();
  const registerWorkspace = useRegisterWorkspace();
  const isDirty = useRequestStore((s) => s.isDirty);
  const discard = useRequestStore((s) => s.discard);

  const active = data?.active ?? "scratch";
  const workspaces = data?.workspaces ?? [];

  // Reuse the unsaved-edits guard pattern from WorkspaceView before changing workspace.
  const guarded = (run: () => void) => {
    if (isDirty()) {
      if (!window.confirm("You have unsaved changes. Discard them?")) return;
      discard();
    }
    run();
  };

  const switchTo = (info: WorkspaceInfo) => switchWorkspace.mutate(info.id);

  const handleChange = (value: string) => {
    if (value === NEW) {
      const name = window.prompt("New workspace name:");
      if (name?.trim()) {
        guarded(() => createWorkspace.mutate(name.trim(), { onSuccess: switchTo }));
      }
      return;
    }
    if (value === ADD) {
      const path = window.prompt("Path to existing project folder:");
      if (path?.trim()) {
        guarded(() => registerWorkspace.mutate(path.trim(), { onSuccess: switchTo }));
      }
      return;
    }
    if (value !== active) guarded(() => switchWorkspace.mutate(value));
  };

  return (
    <Select value={active} onValueChange={handleChange}>
      <SelectTrigger size="sm" className="min-w-44">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {workspaces.map((w) => (
          <SelectItem key={w.id} value={w.id}>
            <span className="flex items-center gap-1.5">
              {w.is_scratch && <span>⌂</span>}
              {w.name}
              {w.kind === "external" && (
                <span className="rounded bg-gray-200 px-1 text-[10px] text-gray-600">
                  external
                </span>
              )}
            </span>
          </SelectItem>
        ))}
        <SelectSeparator />
        <SelectItem value={NEW}>+ New workspace…</SelectItem>
        <SelectItem value={ADD}>⊕ Add existing folder…</SelectItem>
      </SelectContent>
    </Select>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/layout/WorkspaceSwitcher.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/WorkspaceSwitcher.tsx frontend/src/components/layout/WorkspaceSwitcher.test.tsx
git commit -m "feat(frontend): WorkspaceSwitcher dropdown component"
```

---

## Task 7: Frontend — AppBar + App shell, remove WelcomeView

**Files:**
- Create: `frontend/src/components/layout/AppBar.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/views/WorkspaceView.tsx` (root `h-screen` → `h-full`)
- Delete: `frontend/src/views/WelcomeView.tsx`

- [ ] **Step 1: Create `frontend/src/components/layout/AppBar.tsx`**

```tsx
// frontend/src/components/layout/AppBar.tsx
import { useViewStore } from "../../store/viewStore";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

export function AppBar() {
  const setView = useViewStore((s) => s.setView);
  return (
    <nav className="flex shrink-0 items-center gap-4 border-b bg-white px-4 py-2">
      <span className="text-sm font-semibold">🥁 Drummer</span>
      <WorkspaceSwitcher />
      <button
        type="button"
        onClick={() => setView("tutorial")}
        className="ml-auto rounded px-3 py-1 text-xs text-gray-500 hover:text-gray-800"
      >
        Tutorial
      </button>
    </nav>
  );
}
```

- [ ] **Step 2: Rewrite `frontend/src/App.tsx`**

```tsx
import { useEffect } from "react";
import { AppBar } from "./components/layout/AppBar";
import { useProject } from "./api/projects";
import { useProjectStore } from "./store/projectStore";
import { useViewStore } from "./store/viewStore";
import { TutorialView } from "./views/TutorialView";
import { WorkspaceView } from "./views/WorkspaceView";

export default function App() {
  const view = useViewStore((s) => s.view);
  const { data: project, isLoading } = useProject();
  const setProject = useProjectStore((s) => s.setProject);

  useEffect(() => {
    if (project) setProject(project);
  }, [project, setProject]);

  if (view === "tutorial") return <TutorialView />;

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-gray-400">
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

- [ ] **Step 3: Update `frontend/src/views/WorkspaceView.tsx` root element**

Change the outer wrapper (currently `return ( <div className="flex h-screen"> ... )`) to use `h-full` so it fits under the AppBar:

```tsx
  return (
    <div className="flex h-full">
      <TwoPanel
        left={sidebar}
        right={mainArea}
        direction="horizontal"
        defaultSizes={[20, 80]}
      />
    </div>
  );
```

- [ ] **Step 4: Delete the Welcome screen**

```bash
git rm frontend/src/views/WelcomeView.tsx
```

- [ ] **Step 5: Verify type-check and lint**

Run: `cd frontend && npm run check`
Expected: no errors, no unused imports (confirm `WelcomeView` no longer referenced anywhere)

- [ ] **Step 6: Run the frontend tests**

Run: `cd frontend && npx vitest run`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/layout/AppBar.tsx frontend/src/App.tsx frontend/src/views/WorkspaceView.tsx
git commit -m "feat(frontend): persistent AppBar with workspace switcher; remove WelcomeView"
```

---

## Task 8: Docs & roadmap

**Files:**
- Modify: `ROADMAP.md`, `CLAUDE.md`, `README.md`

- [ ] **Step 1: Add Phases 11–14 to `ROADMAP.md`**

Append these rows to the table:

```markdown
| 11 — Workspaces | Central ~/.drummer storage, Scratch catchall, external folders, `drummer` launches, workspace switcher | 🚧 In progress |
| 12 — Theming | Dark / light / system-auto toggle across app + tutorial | ⬜ Planned |
| 13 — Tutorial cohesion | Tutorial drives real app components; persistent Workspace/Tutorial tabs; request + project pane steps | ⬜ Planned |
| 14 — Wikidata GraphQL | Wikidata GraphQL dataset + GraphQL tutorial step | ⬜ Planned |
```

- [ ] **Step 2: Update current phase in `CLAUDE.md`**

Change the line `Current phase: **10 — Distribution**` to:

```markdown
Current phase: **11 — Workspaces**
```

- [ ] **Step 3: Update `README.md` Quick start**

Replace the Quick start commands block with:

```markdown
# Launch Drummer (opens your last workspace, or the Scratch catchall on first run)
drummer

# Open an external project folder (registers it as a workspace)
drummer --project /path/to/my-api
```

And add a short note under it:

```markdown
Workspaces live under `~/.drummer/projects/`. The built-in **Scratch** workspace is always
available for quick, throwaway requests. Use the workspace switcher in the top bar to create
new workspaces or register existing folders, and to cycle between them during a session.
```

- [ ] **Step 4: Run the full gate**

Run: `make check`
Expected: PASS (ruff + pyright + pytest + frontend check)

- [ ] **Step 5: Commit**

```bash
git add ROADMAP.md CLAUDE.md README.md
git commit -m "docs: add Phases 11-14 to roadmap; document workspaces in README"
```

---

## Final verification

- [ ] Run `make check` — all green (ruff, pyright, biome, tsc, pytest unit+integration, vitest).
- [ ] Manual smoke test: `DRUMMER_HOME=/tmp/drummer-smoke venv/bin/python -m drummer` (Ctrl-C after banner), confirm banner reads `Drummer serving 'Scratch'` and `/tmp/drummer-smoke/projects/scratch/.drummer/project.yaml` was created.
