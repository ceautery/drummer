# Phase 4: API + MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI web layer, flat REST routes, SSE send pipeline, SQLite response history, and 12 MCP tools on top of the Phase 3 HTTP engine.

**Architecture:** Single-project mode — launched with `--project <dir>`. A `create_app(project_dir, db_url)` factory stores the project dir, a `CookieJar` singleton, the active environment name, and a SQLAlchemy session factory in `app.state`. FastAPI `Depends` injectors expose these to route handlers. MCP tools are registered as closures over `app` via `fastapi-mcp`. The SSE send endpoint uses `sse-starlette`; network failures emit an `error` event rather than returning an HTTP error status.

**Tech Stack:** FastAPI 0.115+, sse-starlette≥0.10, SQLAlchemy 2.0 + aiosqlite, fastapi-mcp≥0.3, Pydantic v2, pytest-asyncio (asyncio_mode="auto" already configured), httpx ASGITransport for integration tests.

---

### File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `drummer/core/engine.py` | `RequestResult.headers`: `dict[str,str]` → `list[tuple[str,str]]` |
| Modify | `drummer/core/cookies.py` | Add `all_cookies() -> dict[str, dict[str, str]]` |
| Modify | `pyproject.toml` | Add `sse-starlette>=0.10` |
| Create | `drummer/api/app.py` | `create_app(project_dir, db_url) -> FastAPI` |
| Create | `drummer/api/deps.py` | `get_project_dir`, `get_cookie_jar`, `get_db` |
| Create | `drummer/api/db/__init__.py` | Package marker |
| Create | `drummer/api/db/models.py` | `Base`, `ResponseHistoryRecord` ORM model |
| Create | `drummer/api/db/session.py` | `async_session_factory`, `init_db` |
| Create | `drummer/api/routes/__init__.py` | Package marker |
| Create | `drummer/api/routes/requests.py` | CRUD over request `.md` files |
| Create | `drummer/api/routes/environments.py` | Read/write environments |
| Create | `drummer/api/routes/cookies.py` | List / clear `CookieJar` |
| Create | `drummer/api/routes/history.py` | List / clear response history |
| Create | `drummer/api/routes/send.py` | SSE send pipeline |
| Create | `drummer/api/mcp/__init__.py` | Package marker |
| Create | `drummer/api/mcp/tools.py` | 12 MCP tool implementations + `register_mcp_tools` |
| Modify | `drummer/cli.py` | Implement `serve` subcommand (currently a stub) |
| Modify | `tests/unit/test_engine.py` | Update `test_request_result_stores_all_fields` for new header type |
| Create | `tests/integration/conftest.py` | `project_dir`, `app`, `client`, `parse_sse` fixtures |
| Create | `tests/unit/test_db_models.py` | ORM model unit tests |
| Create | `tests/integration/test_requests_routes.py` | CRUD route integration tests |
| Create | `tests/integration/test_environments_routes.py` | Environment route integration tests |
| Create | `tests/integration/test_cookies_routes.py` | Cookie route integration tests |
| Create | `tests/integration/test_history_routes.py` | History route integration tests |
| Create | `tests/integration/test_send_route.py` | SSE send integration tests |
| Create | `tests/integration/test_mcp_tools.py` | MCP tool implementation tests |

---

### Task 1: Fix engine.py header-flattening

`RequestResult.headers` is currently `dict[str, str]`, which collapses duplicate headers (e.g. multiple `Set-Cookie`). Change it to `list[tuple[str, str]]` and update the one test that constructs a `RequestResult` directly.

**Files:**
- Modify: `drummer/core/engine.py`
- Modify: `tests/unit/test_engine.py`

- [ ] **Step 1: Update the failing test first**

In `tests/unit/test_engine.py`, change `test_request_result_stores_all_fields` so it uses the new list-of-tuples type:

```python
def test_request_result_stores_all_fields() -> None:
    elapsed_ms = 42.5
    warnings = ["missing_var"]

    result = RequestResult(
        status_code=_HTTP_OK,
        headers=[("content-type", "application/json")],
        body='{"ok": true}',
        encoding="utf-8",
        elapsed_ms=elapsed_ms,
        url="https://example.com",
        warnings=warnings,
    )
    assert result.status_code == _HTTP_OK
    assert result.elapsed_ms == elapsed_ms
    assert result.warnings == warnings
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
make check
```

Expected: `ValidationError` — `headers` field rejects `dict` input (it hasn't been changed yet).

- [ ] **Step 3: Update `RequestResult` in engine.py**

Change the `headers` field type and the `send()` return statement:

```python
class RequestResult(BaseModel):
    status_code: int
    headers: list[tuple[str, str]]   # changed from dict[str, str]
    body: str
    encoding: str
    elapsed_ms: float
    url: str
    warnings: list[str]
```

In `send()`, replace:
```python
headers=dict(response.headers),
```
with:
```python
headers=list(response.headers.multi_items()),
```

- [ ] **Step 4: Run make check**

```bash
make check
```

Expected: 82 tests pass, 0 errors.

- [ ] **Step 5: Commit**

```bash
git add drummer/core/engine.py tests/unit/test_engine.py
git commit -m "fix: change RequestResult.headers to list[tuple[str,str]] to preserve duplicates"
```

---

### Task 2: Add sse-starlette dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add sse-starlette to pyproject.toml**

In the `dependencies` list, add after `chardet>=5.2`:

```toml
"sse-starlette>=0.10",
```

- [ ] **Step 2: Install**

```bash
make check
```

If pip complains about missing `sse-starlette`, run:

```bash
/Users/curtis/dev/claude_projects/drummer/venv/bin/pip install -e ".[dev]" -q
```

Then re-run `make check` to confirm 82 tests still pass.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add sse-starlette dependency"
```

---

### Task 3: Database layer

**Files:**
- Create: `drummer/api/db/__init__.py`
- Create: `drummer/api/db/models.py`
- Create: `drummer/api/db/session.py`
- Create: `tests/unit/test_db_models.py`

- [ ] **Step 1: Write failing unit tests**

Create `tests/unit/test_db_models.py`:

```python
import json
from datetime import datetime, timezone

from drummer.api.db.models import ResponseHistoryRecord


def test_record_to_dict_roundtrips_fields() -> None:
    sent = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
    record = ResponseHistoryRecord(
        id="abc-123",
        sent_at=sent,
        request_path="auth/login.md",
        request_name="Login",
        environment="local",
        method="POST",
        url="https://api.example.com/login",
        status_code=200,
        elapsed_ms=42.5,
        request_headers=json.dumps([["content-type", "application/json"]]),
        request_body='{"user": "alice"}',
        response_headers=json.dumps([["set-cookie", "session=abc"]]),
        response_body='{"token": "xyz"}',
        encoding="utf-8",
        warnings=json.dumps(["missing_var"]),
    )
    d = record.to_dict()
    assert d["id"] == "abc-123"
    assert d["sent_at"] == "2026-05-26T12:00:00+00:00"
    assert d["status_code"] == 200
    assert d["elapsed_ms"] == 42.5
    assert d["request_headers"] == [["content-type", "application/json"]]
    assert d["response_headers"] == [["set-cookie", "session=abc"]]
    assert d["warnings"] == ["missing_var"]


def test_record_to_dict_returns_parsed_json_fields() -> None:
    record = ResponseHistoryRecord(
        id="x",
        sent_at=datetime.now(timezone.utc),
        request_path="r.md",
        request_name="R",
        environment="local",
        method="GET",
        url="https://x.com",
        status_code=200,
        elapsed_ms=1.0,
        request_headers=json.dumps([]),
        request_body="",
        response_headers=json.dumps([["content-type", "text/plain"], ["x-custom", "foo"]]),
        response_body="hello",
        encoding="utf-8",
        warnings=json.dumps([]),
    )
    d = record.to_dict()
    assert isinstance(d["response_headers"], list)
    assert len(d["response_headers"]) == 2
```

- [ ] **Step 2: Run to confirm failure**

```bash
make check
```

Expected: `ModuleNotFoundError: No module named 'drummer.api.db'`

- [ ] **Step 3: Create package markers and models**

Create `drummer/api/db/__init__.py` (empty).

Create `drummer/api/db/models.py`:

```python
import json
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ResponseHistoryRecord(Base):
    __tablename__ = "response_history"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_path: Mapped[str] = mapped_column(Text, nullable=False)
    request_name: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    elapsed_ms: Mapped[float] = mapped_column(Float, nullable=False)
    request_headers: Mapped[str] = mapped_column(Text, nullable=False)
    request_body: Mapped[str] = mapped_column(Text, nullable=False)
    response_headers: Mapped[str] = mapped_column(Text, nullable=False)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)
    encoding: Mapped[str] = mapped_column(String(64), nullable=False)
    warnings: Mapped[str] = mapped_column(Text, nullable=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "sent_at": self.sent_at.isoformat(),
            "request_path": self.request_path,
            "request_name": self.request_name,
            "environment": self.environment,
            "method": self.method,
            "url": self.url,
            "status_code": self.status_code,
            "elapsed_ms": self.elapsed_ms,
            "request_headers": json.loads(self.request_headers),
            "request_body": self.request_body,
            "response_headers": json.loads(self.response_headers),
            "response_body": self.response_body,
            "encoding": self.encoding,
            "warnings": json.loads(self.warnings),
        }
```

Create `drummer/api/db/session.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from drummer.api.db.models import Base


def async_session_factory(db_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(db_url)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(db_url: str) -> None:
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
```

- [ ] **Step 4: Run make check**

```bash
make check
```

Expected: 84 tests pass (2 new), 0 errors.

- [ ] **Step 5: Commit**

```bash
git add drummer/api/db/ tests/unit/test_db_models.py
git commit -m "feat: add SQLAlchemy ORM models and session factory for response history"
```

---

### Task 4: App factory, dependencies, and integration test infrastructure

**Files:**
- Create: `drummer/api/app.py`
- Create: `drummer/api/deps.py`
- Create: `drummer/api/routes/__init__.py`
- Create: `drummer/api/mcp/__init__.py`
- Create: `tests/integration/conftest.py`

- [ ] **Step 1: Write a minimal smoke test**

Create `tests/integration/conftest.py`:

```python
import json
from pathlib import Path
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.core.storage.project import create_project


@pytest_asyncio.fixture
async def project_dir(tmp_path: Path) -> Path:
    create_project(tmp_path, "Test Project")
    return tmp_path


@pytest_asyncio.fixture
async def client(project_dir: Path) -> AsyncGenerator[AsyncClient, None]:
    application = create_app(
        project_dir=project_dir,
        db_url="sqlite+aiosqlite:///:memory:",
    )
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as ac:
        yield ac


class MockTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        status_code: int = 200,
        headers: list[tuple[str, str]] | None = None,
        content: bytes = b"",
    ) -> None:
        self._status_code = status_code
        self._headers = headers or [("content-type", "application/json")]
        self._content = content

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=self._status_code,
            headers=self._headers,
            content=self._content,
            request=request,
        )


@pytest_asyncio.fixture
async def client_with_mock(
    project_dir: Path,
) -> AsyncGenerator[AsyncClient, None]:
    application = create_app(
        project_dir=project_dir,
        db_url="sqlite+aiosqlite:///:memory:",
    )
    application.state.transport = MockTransport(
        status_code=200,
        headers=[("content-type", "application/json")],
        content=b'{"ok": true}',
    )
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as ac:
        yield ac


def parse_sse(text: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    current: dict[str, object] = {}
    for line in text.split("\n"):
        if line.startswith("event:"):
            current["event"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current["data"] = json.loads(line[len("data:"):].strip())
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events
```

Now write the smoke test in `tests/integration/test_requests_routes.py` (partial — just imports):

```python
# This file will be filled in Task 5. Create it now as a placeholder to confirm the app boots.
```

Actually, write a real smoke test instead in `tests/integration/test_requests_routes.py`:

```python
async def test_app_boots(client) -> None:
    response = await client.get("/api/requests")
    assert response.status_code == 200
```

- [ ] **Step 2: Run to confirm failure**

```bash
make check
```

Expected: `ModuleNotFoundError: No module named 'drummer.api.app'`

- [ ] **Step 3: Create package markers and app factory**

Create `drummer/api/routes/__init__.py` (empty).
Create `drummer/api/mcp/__init__.py` (empty).

Create `drummer/api/app.py`:

```python
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI

from drummer.api.db.session import async_session_factory, init_db
from drummer.core.cookies import CookieJar

_DEFAULT_DB = str(Path.home() / ".local" / "share" / "drummer" / "history.db")


def create_app(
    project_dir: Path,
    db_url: str = f"sqlite+aiosqlite:///{_DEFAULT_DB}",
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        await init_db(db_url)
        yield

    app = FastAPI(title="Drummer", lifespan=lifespan)
    app.state.project_dir = project_dir
    app.state.cookie_jar = CookieJar()
    app.state.active_environment = "local"
    app.state.db_factory = async_session_factory(db_url)
    app.state.transport = None  # overridden in tests

    from drummer.api.routes import requests as req_routes
    from drummer.api.routes import environments as env_routes
    from drummer.api.routes import send as send_routes
    from drummer.api.routes import history as history_routes
    from drummer.api.routes import cookies as cookie_routes

    app.include_router(req_routes.router, prefix="/api")
    app.include_router(env_routes.router, prefix="/api")
    app.include_router(send_routes.router, prefix="/api")
    app.include_router(history_routes.router, prefix="/api")
    app.include_router(cookie_routes.router, prefix="/api")

    from fastapi_mcp import FastApiMCP
    from drummer.api.mcp.tools import register_mcp_tools

    mcp = FastApiMCP(app)
    register_mcp_tools(mcp, app)
    mcp.mount()

    return app
```

Create `drummer/api/deps.py`:

```python
from pathlib import Path
from typing import AsyncGenerator, cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drummer.core.cookies import CookieJar


def get_project_dir(request: Request) -> Path:
    return cast(Path, request.app.state.project_dir)


def get_cookie_jar(request: Request) -> CookieJar:
    return cast(CookieJar, request.app.state.cookie_jar)


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    factory = cast(async_sessionmaker[AsyncSession], request.app.state.db_factory)
    async with factory() as session:
        yield session
```

The routers imported in `app.py` don't exist yet, so stub them now. Create `drummer/api/routes/requests.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/requests")
async def list_requests_route() -> list[dict[str, str]]:
    return []
```

Create stubs for the other four routers (all return empty or 200):

`drummer/api/routes/environments.py`:
```python
from fastapi import APIRouter

router = APIRouter()
```

`drummer/api/routes/send.py`:
```python
from fastapi import APIRouter

router = APIRouter()
```

`drummer/api/routes/history.py`:
```python
from fastapi import APIRouter

router = APIRouter()
```

`drummer/api/routes/cookies.py`:
```python
from fastapi import APIRouter

router = APIRouter()
```

Create `drummer/api/mcp/tools.py` stub:

```python
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP


def register_mcp_tools(mcp: FastApiMCP, app: FastAPI) -> None:
    pass
```

- [ ] **Step 4: Run make check**

```bash
make check
```

Expected: 85 tests pass (1 new smoke test), 0 errors.

- [ ] **Step 5: Commit**

```bash
git add drummer/api/app.py drummer/api/deps.py drummer/api/routes/ drummer/api/mcp/ tests/integration/conftest.py tests/integration/test_requests_routes.py
git commit -m "feat: add app factory, deps, route stubs, and integration test infrastructure"
```

---

### Task 5: Request file CRUD routes

**Files:**
- Modify: `drummer/api/routes/requests.py` (replace stub)
- Modify: `tests/integration/test_requests_routes.py` (replace smoke test)

- [ ] **Step 1: Write failing tests**

Replace `tests/integration/test_requests_routes.py`:

```python
from pathlib import Path


async def test_list_requests_empty(client) -> None:
    response = await client.get("/api/requests")
    assert response.status_code == 200
    assert response.json() == []


async def test_create_and_get_request(client, project_dir: Path) -> None:
    payload = {
        "path": "users/list.md",
        "name": "List Users",
        "method": "GET",
        "url": "https://api.example.com/users",
        "headers": {"Accept": "application/json"},
        "body": "fetch all users",
    }
    create_resp = await client.post("/api/requests", json=payload)
    assert create_resp.status_code == 201
    assert (project_dir / "users" / "list.md").exists()

    get_resp = await client.get("/api/requests/users/list.md")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["frontmatter"]["name"] == "List Users"
    assert data["frontmatter"]["method"] == "GET"
    assert data["body"] == "fetch all users"


async def test_update_request(client, project_dir: Path) -> None:
    await client.post("/api/requests", json={
        "path": "ping.md", "name": "Ping", "method": "GET", "url": "https://x.com", "headers": {}, "body": "",
    })
    update_resp = await client.put("/api/requests/ping.md", json={
        "path": "ping.md", "name": "Ping Updated", "method": "POST", "url": "https://x.com/ping", "headers": {}, "body": "body",
    })
    assert update_resp.status_code == 200
    get_resp = await client.get("/api/requests/ping.md")
    assert get_resp.json()["frontmatter"]["name"] == "Ping Updated"
    assert get_resp.json()["frontmatter"]["method"] == "POST"


async def test_delete_request(client, project_dir: Path) -> None:
    await client.post("/api/requests", json={
        "path": "temp.md", "name": "Temp", "method": "GET", "url": "https://x.com", "headers": {}, "body": "",
    })
    assert (project_dir / "temp.md").exists()
    del_resp = await client.delete("/api/requests/temp.md")
    assert del_resp.status_code == 204
    assert not (project_dir / "temp.md").exists()


async def test_get_missing_request_returns_404(client) -> None:
    response = await client.get("/api/requests/does-not-exist.md")
    assert response.status_code == 404


async def test_list_requests_returns_summaries(client, project_dir: Path) -> None:
    await client.post("/api/requests", json={
        "path": "a.md", "name": "A", "method": "GET", "url": "https://a.com", "headers": {}, "body": "",
    })
    await client.post("/api/requests", json={
        "path": "b.md", "name": "B", "method": "POST", "url": "https://b.com", "headers": {}, "body": "",
    })
    response = await client.get("/api/requests")
    items = response.json()
    assert len(items) == 2
    paths = {item["path"] for item in items}
    assert "a.md" in paths
    assert "b.md" in paths
```

- [ ] **Step 2: Run to confirm failure**

```bash
make check
```

Expected: 5 new failures — routes not implemented yet.

- [ ] **Step 3: Implement requests.py**

Replace `drummer/api/routes/requests.py`:

```python
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from drummer.api.deps import get_project_dir
from drummer.core.storage.formats import (
    RequestFile,
    RequestFrontmatter,
    parse_request_file,
    write_request_file,
)
from drummer.core.storage.project import list_requests

router = APIRouter()


class CreateRequestBody(BaseModel):
    path: str
    name: str
    method: str = "GET"
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = ""


class RequestSummary(BaseModel):
    path: str
    name: str
    method: str
    url: str


class RequestDetail(BaseModel):
    path: str
    frontmatter: RequestFrontmatter
    body: str


@router.get("/requests", response_model=list[RequestSummary])
async def list_requests_route(
    project_dir: Path = Depends(get_project_dir),
) -> list[RequestSummary]:
    paths = list_requests(project_dir)
    result = []
    for p in paths:
        rf = parse_request_file(p)
        result.append(RequestSummary(
            path=str(p.relative_to(project_dir)),
            name=rf.frontmatter.name,
            method=rf.frontmatter.method,
            url=rf.frontmatter.url,
        ))
    return result


@router.get("/requests/{path:path}", response_model=RequestDetail)
async def get_request_route(
    path: str,
    project_dir: Path = Depends(get_project_dir),
) -> RequestDetail:
    full_path = project_dir / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Request not found: {path}")
    rf = parse_request_file(full_path)
    return RequestDetail(path=path, frontmatter=rf.frontmatter, body=rf.body)


@router.post("/requests", response_model=RequestSummary, status_code=201)
async def create_request_route(
    body: CreateRequestBody,
    project_dir: Path = Depends(get_project_dir),
) -> RequestSummary:
    full_path = project_dir / body.path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    fm = RequestFrontmatter(
        name=body.name,
        method=body.method,  # type: ignore[arg-type]
        url=body.url,
        headers=body.headers,
    )
    write_request_file(RequestFile(frontmatter=fm, body=body.body, path=full_path))
    return RequestSummary(path=body.path, name=body.name, method=body.method, url=body.url)


@router.put("/requests/{path:path}", response_model=RequestSummary)
async def update_request_route(
    path: str,
    body: CreateRequestBody,
    project_dir: Path = Depends(get_project_dir),
) -> RequestSummary:
    full_path = project_dir / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Request not found: {path}")
    fm = RequestFrontmatter(
        name=body.name,
        method=body.method,  # type: ignore[arg-type]
        url=body.url,
        headers=body.headers,
    )
    write_request_file(RequestFile(frontmatter=fm, body=body.body, path=full_path))
    return RequestSummary(path=path, name=body.name, method=body.method, url=body.url)


@router.delete("/requests/{path:path}", status_code=204)
async def delete_request_route(
    path: str,
    project_dir: Path = Depends(get_project_dir),
) -> None:
    full_path = project_dir / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Request not found: {path}")
    full_path.unlink()
```

**Note on `# type: ignore[arg-type]`:** `body.method` is `str` but `RequestFrontmatter` expects the `HttpMethod` literal. Pyright will flag this. Fix it by adding a validator or by using `model_validate`:

Replace the two `RequestFrontmatter(...)` calls with:

```python
    fm = RequestFrontmatter.model_validate({
        "name": body.name,
        "method": body.method,
        "url": body.url,
        "headers": body.headers,
    })
```

This avoids the type error because `model_validate` accepts `dict[str, Any]`.

- [ ] **Step 4: Run make check**

```bash
make check
```

Expected: All tests pass including the 6 new request route tests. Fix any Pyright errors before moving on.

- [ ] **Step 5: Commit**

```bash
git add drummer/api/routes/requests.py tests/integration/test_requests_routes.py
git commit -m "feat: implement request file CRUD routes"
```

---

### Task 6: Environment routes

**Files:**
- Modify: `drummer/api/routes/environments.py` (replace stub)
- Create: `tests/integration/test_environments_routes.py`

- [ ] **Step 1: Write failing tests**

Create `tests/integration/test_environments_routes.py`:

```python
from pathlib import Path


async def test_list_environments_returns_local(client) -> None:
    response = await client.get("/api/environments")
    assert response.status_code == 200
    envs = response.json()
    assert len(envs) == 1
    assert envs[0]["name"] == "local"


async def test_get_environment(client) -> None:
    response = await client.get("/api/environments/local")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "local"
    assert isinstance(data["variables"], dict)


async def test_update_environment_variables(client) -> None:
    payload = {"name": "local", "variables": {"base_url": "https://api.example.com", "token": "abc123"}}
    put_resp = await client.put("/api/environments/local", json=payload)
    assert put_resp.status_code == 200

    get_resp = await client.get("/api/environments/local")
    variables = get_resp.json()["variables"]
    assert variables["base_url"] == "https://api.example.com"
    assert variables["token"] == "abc123"


async def test_get_missing_environment_returns_404(client) -> None:
    response = await client.get("/api/environments/staging")
    assert response.status_code == 404
```

- [ ] **Step 2: Run to confirm failure**

```bash
make check
```

Expected: 4 new failures.

- [ ] **Step 3: Implement environments.py**

Replace `drummer/api/routes/environments.py`:

```python
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from drummer.api.deps import get_project_dir
from drummer.core.storage.project import (
    Environment,
    list_environments,
    load_environment,
    save_environment,
)

router = APIRouter()


class EnvironmentSummary(BaseModel):
    name: str
    variable_count: int


class EnvironmentDetail(BaseModel):
    name: str
    variables: dict[str, str] = Field(default_factory=dict)


@router.get("/environments", response_model=list[EnvironmentSummary])
async def list_environments_route(
    project_dir: Path = Depends(get_project_dir),
) -> list[EnvironmentSummary]:
    envs = list_environments(project_dir)
    return [EnvironmentSummary(name=e.name, variable_count=len(e.variables)) for e in envs]


@router.get("/environments/{name}", response_model=EnvironmentDetail)
async def get_environment_route(
    name: str,
    project_dir: Path = Depends(get_project_dir),
) -> EnvironmentDetail:
    env_path = project_dir / ".drummer" / "environments" / f"{name}.yaml"
    if not env_path.exists():
        raise HTTPException(status_code=404, detail=f"Environment not found: {name}")
    env = load_environment(env_path)
    return EnvironmentDetail(name=env.name, variables=env.variables)


@router.put("/environments/{name}", response_model=EnvironmentDetail)
async def update_environment_route(
    name: str,
    body: EnvironmentDetail,
    project_dir: Path = Depends(get_project_dir),
) -> EnvironmentDetail:
    env = Environment(name=name, variables=body.variables)
    save_environment(env, project_dir)
    return EnvironmentDetail(name=name, variables=body.variables)
```

- [ ] **Step 4: Run make check**

```bash
make check
```

Expected: All tests pass. Fix any Pyright errors.

- [ ] **Step 5: Commit**

```bash
git add drummer/api/routes/environments.py tests/integration/test_environments_routes.py
git commit -m "feat: implement environment routes"
```

---

### Task 7: Cookie routes and CookieJar.all_cookies()

`CookieJar` needs an `all_cookies()` method to expose its internal store.

**Files:**
- Modify: `drummer/core/cookies.py` (add `all_cookies`)
- Modify: `drummer/api/routes/cookies.py` (replace stub)
- Create: `tests/integration/test_cookies_routes.py`

- [ ] **Step 1: Write failing tests**

Create `tests/integration/test_cookies_routes.py`:

```python
async def test_list_cookies_empty(client) -> None:
    response = await client.get("/api/cookies")
    assert response.status_code == 200
    assert response.json() == {}


async def test_clear_cookies(client_with_mock, project_dir) -> None:
    # Seed a request file and send to populate the jar
    import pytest
    from pathlib import Path

    req_path = project_dir / "ping.md"
    req_path.write_text(
        "---\nname: Ping\nmethod: GET\nurl: https://api.example.com/ping\n---\n",
        encoding="utf-8",
    )
    await client_with_mock.post("/api/send", json={"path": "ping.md"})

    del_resp = await client_with_mock.delete("/api/cookies")
    assert del_resp.status_code == 200

    list_resp = await client_with_mock.get("/api/cookies")
    assert list_resp.json() == {}
```

- [ ] **Step 2: Run to confirm failure**

```bash
make check
```

Expected: 2 new failures.

- [ ] **Step 3: Add `all_cookies()` to CookieJar**

In `drummer/core/cookies.py`, add after `clear()`:

```python
def all_cookies(self) -> dict[str, dict[str, str]]:
    return {hostname: dict(cookies) for hostname, cookies in self._store.items()}
```

- [ ] **Step 4: Implement cookies.py route**

Replace `drummer/api/routes/cookies.py`:

```python
from fastapi import APIRouter, Depends

from drummer.api.deps import get_cookie_jar
from drummer.core.cookies import CookieJar

router = APIRouter()


@router.get("/cookies")
async def list_cookies_route(
    cookie_jar: CookieJar = Depends(get_cookie_jar),
) -> dict[str, dict[str, str]]:
    return cookie_jar.all_cookies()


@router.delete("/cookies")
async def clear_cookies_route(
    cookie_jar: CookieJar = Depends(get_cookie_jar),
) -> dict[str, str]:
    cookie_jar.clear()
    return {"status": "cleared"}
```

- [ ] **Step 5: Run make check**

```bash
make check
```

Expected: All tests pass. The `test_clear_cookies` test depends on the send route — if the send route isn't implemented yet, that test will fail. That's acceptable; it will pass after Task 9. Mark it with `@pytest.mark.skip(reason="requires send route — Task 9")` temporarily if needed.

Actually: write the test without the send dependency. Just populate the jar directly by calling the cookie jar through the fixture:

Replace `test_clear_cookies` with:

```python
async def test_clear_cookies(client, project_dir) -> None:
    from drummer.api.app import create_app
    from httpx import ASGITransport, AsyncClient

    application = create_app(
        project_dir=project_dir,
        db_url="sqlite+aiosqlite:///:memory:",
    )
    # Manually seed the cookie jar
    application.state.cookie_jar.update_from_response(
        "https://api.example.com/login", ["session=abc123"]
    )
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as ac:
        list_resp = await ac.get("/api/cookies")
        assert list_resp.json() == {"api.example.com": {"session": "abc123"}}

        del_resp = await ac.delete("/api/cookies")
        assert del_resp.status_code == 200

        empty_resp = await ac.get("/api/cookies")
        assert empty_resp.json() == {}
```

- [ ] **Step 6: Run make check**

```bash
make check
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add drummer/core/cookies.py drummer/api/routes/cookies.py tests/integration/test_cookies_routes.py
git commit -m "feat: add CookieJar.all_cookies() and implement cookie routes"
```

---

### Task 8: History routes

**Files:**
- Modify: `drummer/api/routes/history.py` (replace stub)
- Create: `tests/integration/test_history_routes.py`

- [ ] **Step 1: Write failing tests**

Create `tests/integration/test_history_routes.py`:

```python
import json
from datetime import datetime, timezone

from drummer.api.db.models import ResponseHistoryRecord


async def _seed_record(app_state, i: int = 0) -> str:
    """Insert a history record directly into the db and return its id."""
    record_id = f"test-id-{i}"
    async with app_state.db_factory() as session:
        record = ResponseHistoryRecord(
            id=record_id,
            sent_at=datetime.now(timezone.utc),
            request_path=f"request-{i}.md",
            request_name=f"Request {i}",
            environment="local",
            method="GET",
            url="https://api.example.com",
            status_code=200,
            elapsed_ms=10.0,
            request_headers=json.dumps([]),
            request_body="",
            response_headers=json.dumps([("content-type", "application/json")]),
            response_body='{"ok": true}',
            encoding="utf-8",
            warnings=json.dumps([]),
        )
        session.add(record)
        await session.commit()
    return record_id


async def test_list_history_empty(client) -> None:
    response = await client.get("/api/history")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_history_returns_records(client) -> None:
    from drummer.api.app import create_app
    from httpx import ASGITransport, AsyncClient
    from pathlib import Path
    from drummer.core.storage.project import create_project
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        create_project(project_dir, "Test")
        application = create_app(project_dir=project_dir, db_url="sqlite+aiosqlite:///:memory:")

        async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
            await ac.get("/api/history")  # trigger lifespan

        await _seed_record(application.state, 0)
        await _seed_record(application.state, 1)

        async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
            response = await ac.get("/api/history")
            records = response.json()
            assert len(records) == 2
            assert records[0]["id"] in ("test-id-0", "test-id-1")


async def test_list_history_filter_by_path(client) -> None:
    from drummer.api.app import create_app
    from httpx import ASGITransport, AsyncClient
    from pathlib import Path
    from drummer.core.storage.project import create_project
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        create_project(project_dir, "Test")
        application = create_app(project_dir=project_dir, db_url="sqlite+aiosqlite:///:memory:")

        await _seed_record(application.state, 0)
        await _seed_record(application.state, 1)

        async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
            response = await ac.get("/api/history?request_path=request-0.md")
            records = response.json()
            assert len(records) == 1
            assert records[0]["request_path"] == "request-0.md"


async def test_delete_history(client) -> None:
    from drummer.api.app import create_app
    from httpx import ASGITransport, AsyncClient
    from pathlib import Path
    from drummer.core.storage.project import create_project
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        create_project(project_dir, "Test")
        application = create_app(project_dir=project_dir, db_url="sqlite+aiosqlite:///:memory:")

        await _seed_record(application.state, 0)

        async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
            del_resp = await ac.delete("/api/history")
            assert del_resp.status_code == 200

            list_resp = await ac.get("/api/history")
            assert list_resp.json() == []
```

**Note:** These tests create their own app instances to control the db state cleanly.

- [ ] **Step 2: Run to confirm failure**

```bash
make check
```

Expected: new failures from missing routes.

- [ ] **Step 3: Implement history.py**

Replace `drummer/api/routes/history.py`:

```python
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from drummer.api.deps import get_db
from drummer.api.db.models import ResponseHistoryRecord

router = APIRouter()


@router.get("/history")
async def list_history_route(
    request_path: str = "",
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    stmt = (
        select(ResponseHistoryRecord)
        .order_by(ResponseHistoryRecord.sent_at.desc())
        .limit(limit)
    )
    if request_path:
        stmt = stmt.where(ResponseHistoryRecord.request_path == request_path)
    result = await db.execute(stmt)
    return [r.to_dict() for r in result.scalars().all()]


@router.delete("/history")
async def delete_history_route(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await db.execute(delete(ResponseHistoryRecord))
    await db.commit()
    return {"status": "cleared"}
```

- [ ] **Step 4: Run make check**

```bash
make check
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add drummer/api/routes/history.py tests/integration/test_history_routes.py
git commit -m "feat: implement response history routes"
```

---

### Task 9: SSE send route

**Files:**
- Modify: `drummer/api/routes/send.py` (replace stub)
- Create: `tests/integration/test_send_route.py`

- [ ] **Step 1: Write failing tests**

Create `tests/integration/test_send_route.py`:

```python
import json
from pathlib import Path

from tests.integration.conftest import MockTransport, parse_sse
from drummer.api.app import create_app
from httpx import ASGITransport, AsyncClient
from drummer.core.storage.project import create_project


def _make_app(project_dir: Path, transport=None, status_code: int = 200, content: bytes = b'{"ok":true}'):
    application = create_app(project_dir=project_dir, db_url="sqlite+aiosqlite:///:memory:")
    if transport is not None:
        application.state.transport = transport
    else:
        application.state.transport = MockTransport(
            status_code=status_code,
            headers=[("content-type", "application/json")],
            content=content,
        )
    return application


async def test_send_success_emits_sse_events(project_dir: Path) -> None:
    (project_dir / "ping.md").write_text(
        "---\nname: Ping\nmethod: GET\nurl: https://api.example.com/ping\n---\n",
        encoding="utf-8",
    )
    app = _make_app(project_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/send", json={"path": "ping.md"})
    assert response.status_code == 200
    events = parse_sse(response.text)
    event_names = [e["event"] for e in events]
    assert "status" in event_names
    assert "headers" in event_names
    assert "body" in event_names
    assert "done" in event_names

    status_event = next(e for e in events if e["event"] == "status")
    assert status_event["data"]["status_code"] == 200

    done_event = next(e for e in events if e["event"] == "done")
    assert "history_id" in done_event["data"]


async def test_send_writes_history_record(project_dir: Path) -> None:
    (project_dir / "ping.md").write_text(
        "---\nname: Ping\nmethod: GET\nurl: https://api.example.com/ping\n---\n",
        encoding="utf-8",
    )
    app = _make_app(project_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/send", json={"path": "ping.md"})
        history = await ac.get("/api/history")
    records = history.json()
    assert len(records) == 1
    assert records[0]["request_name"] == "Ping"
    assert records[0]["status_code"] == 200


async def test_send_network_failure_emits_error_event(project_dir: Path) -> None:
    import httpx

    class FailTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

    (project_dir / "ping.md").write_text(
        "---\nname: Ping\nmethod: GET\nurl: https://api.example.com/ping\n---\n",
        encoding="utf-8",
    )
    app = _make_app(project_dir, transport=FailTransport())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/send", json={"path": "ping.md"})
    events = parse_sse(response.text)
    assert any(e["event"] == "error" for e in events)
    assert not any(e["event"] == "done" for e in events)


async def test_send_no_history_on_failure(project_dir: Path) -> None:
    import httpx

    class FailTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

    (project_dir / "ping.md").write_text(
        "---\nname: Ping\nmethod: GET\nurl: https://api.example.com/ping\n---\n",
        encoding="utf-8",
    )
    app = _make_app(project_dir, transport=FailTransport())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/send", json={"path": "ping.md"})
        history = await ac.get("/api/history")
    assert history.json() == []


async def test_send_with_variable_overrides(project_dir: Path) -> None:
    (project_dir / "ping.md").write_text(
        "---\nname: Ping\nmethod: GET\nurl: '{{base_url}}/ping'\n---\n",
        encoding="utf-8",
    )
    app = _make_app(project_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/send", json={
            "path": "ping.md",
            "overrides": {"base_url": "https://api.example.com"},
        })
    events = parse_sse(response.text)
    status_event = next(e for e in events if e["event"] == "status")
    assert "api.example.com" in status_event["data"]["url"]
```

- [ ] **Step 2: Run to confirm failure**

```bash
make check
```

Expected: 5 new failures.

- [ ] **Step 3: Implement send.py**

Replace `drummer/api/routes/send.py`:

```python
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, cast
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from drummer.api.db.models import ResponseHistoryRecord
from drummer.api.deps import get_cookie_jar, get_project_dir
from drummer.core.cookies import CookieJar
from drummer.core.engine import send as engine_send
from drummer.core.storage.formats import parse_request_file
from drummer.core.storage.project import load_environment
from drummer.core.variables import resolve

router = APIRouter()


class SendRequest(BaseModel):
    path: str
    environment: str = ""
    overrides: dict[str, str] = Field(default_factory=dict)


@router.post("/send")
async def send_request_route(
    body: SendRequest,
    request: Request,
    project_dir: Path = Depends(get_project_dir),
    cookie_jar: CookieJar = Depends(get_cookie_jar),
) -> EventSourceResponse:
    environment = body.environment or cast(str, request.app.state.active_environment)
    transport = cast(httpx.AsyncBaseTransport | None, request.app.state.transport)
    db_factory = request.app.state.db_factory

    async def generate() -> AsyncGenerator[dict[str, str], None]:
        try:
            req_path = project_dir / body.path
            request_file = parse_request_file(req_path)
            env_path = project_dir / ".drummer" / "environments" / f"{environment}.yaml"
            env = load_environment(env_path)
            variables: dict[str, str] = {**env.variables, **body.overrides}
            resolved = resolve(request_file, variables)

            result = await engine_send(resolved, cookie_jar, transport=transport)

            yield {"event": "status", "data": json.dumps({"status_code": result.status_code, "url": result.url})}
            yield {"event": "headers", "data": json.dumps(result.headers)}
            yield {"event": "body", "data": json.dumps({"body": result.body, "encoding": result.encoding, "elapsed_ms": result.elapsed_ms})}

            record_id = str(uuid4())
            async with db_factory() as session:
                record = ResponseHistoryRecord(
                    id=record_id,
                    sent_at=datetime.now(timezone.utc),
                    request_path=body.path,
                    request_name=request_file.frontmatter.name,
                    environment=environment,
                    method=resolved.method,
                    url=result.url,
                    status_code=result.status_code,
                    elapsed_ms=result.elapsed_ms,
                    request_headers=json.dumps(list(resolved.headers.items())),
                    request_body=resolved.body,
                    response_headers=json.dumps(result.headers),
                    response_body=result.body,
                    encoding=result.encoding,
                    warnings=json.dumps(result.warnings),
                )
                session.add(record)
                await session.commit()

            yield {"event": "done", "data": json.dumps({"history_id": record_id})}

        except Exception as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}

    return EventSourceResponse(generate())
```

- [ ] **Step 4: Run make check**

```bash
make check
```

Expected: All tests pass. If Pyright complains about `EventSourceResponse` as a return type annotation on a FastAPI route, remove the return annotation from `send_request_route` (FastAPI infers the response type from the returned object):

```python
@router.post("/send")
async def send_request_route(
    body: SendRequest,
    request: Request,
    project_dir: Path = Depends(get_project_dir),
    cookie_jar: CookieJar = Depends(get_cookie_jar),
):
```

Fix any remaining Pyright errors before committing.

- [ ] **Step 5: Commit**

```bash
git add drummer/api/routes/send.py tests/integration/test_send_route.py
git commit -m "feat: implement SSE send route with history recording"
```

---

### Task 10: MCP tools

**Files:**
- Modify: `drummer/api/mcp/tools.py` (replace stub)
- Create: `tests/integration/test_mcp_tools.py`

The 12 tool implementations are pure async functions (`_impl` variants) plus a `register_mcp_tools` function that wraps them as closures over `app` and registers them with fastapi-mcp.

**Note on fastapi-mcp tool registration:** fastapi-mcp 0.3 exposes `@mcp.tool()` as a decorator for registering custom tools. If the installed version does not support `@mcp.tool()`, check the library's README for the equivalent API (it may be `mcp.add_tool()` or the underlying `mcp._mcp_server.tool()`).

- [ ] **Step 1: Write failing tests**

Create `tests/integration/test_mcp_tools.py`:

```python
from pathlib import Path

from drummer.core.storage.project import create_project, save_environment, Environment
from drummer.api.mcp.tools import (
    list_requests_impl,
    get_request_impl,
    create_request_impl,
    update_request_impl,
    send_request_impl,
    get_history_impl,
    list_environments_impl,
    get_environment_impl,
    set_variable_impl,
    switch_environment_impl,
    list_cookies_impl,
    clear_cookies_impl,
)
from drummer.core.cookies import CookieJar


async def test_list_requests_impl_empty(project_dir: Path) -> None:
    result = await list_requests_impl(project_dir)
    assert result == []


async def test_create_and_get_request_impl(project_dir: Path, tmp_path: Path) -> None:
    await create_request_impl(project_dir, "api/users.md", "List Users", "GET", "https://api.example.com/users")
    assert (project_dir / "api" / "users.md").exists()

    items = await list_requests_impl(project_dir)
    assert len(items) == 1
    assert items[0]["name"] == "List Users"

    detail = await get_request_impl(project_dir, "api/users.md")
    assert detail["name"] == "List Users"
    assert detail["method"] == "GET"


async def test_update_request_impl(project_dir: Path) -> None:
    await create_request_impl(project_dir, "ping.md", "Ping", "GET", "https://x.com")
    await update_request_impl(project_dir, "ping.md", name="Ping v2", url="https://x.com/v2")
    detail = await get_request_impl(project_dir, "ping.md")
    assert detail["name"] == "Ping v2"
    assert detail["url"] == "https://x.com/v2"


async def test_list_environments_impl(project_dir: Path) -> None:
    envs = await list_environments_impl(project_dir)
    assert len(envs) == 1
    assert envs[0]["name"] == "local"


async def test_get_environment_impl(project_dir: Path) -> None:
    variables = await get_environment_impl(project_dir, "local")
    assert isinstance(variables, dict)


async def test_set_variable_impl(project_dir: Path) -> None:
    await set_variable_impl(project_dir, "local", "base_url", "https://api.example.com")
    variables = await get_environment_impl(project_dir, "local")
    assert variables["base_url"] == "https://api.example.com"


async def test_switch_environment_impl(project_dir: Path) -> None:
    class FakeState:
        active_environment = "local"

    state = FakeState()
    result = await switch_environment_impl(state, "staging")
    assert result == {"active_environment": "staging"}
    assert state.active_environment == "staging"


async def test_list_and_clear_cookies_impl() -> None:
    jar = CookieJar()
    jar.update_from_response("https://api.example.com/login", ["session=abc"])
    cookies = await list_cookies_impl(jar)
    assert "api.example.com" in cookies

    await clear_cookies_impl(jar)
    assert await list_cookies_impl(jar) == {}
```

- [ ] **Step 2: Run to confirm failure**

```bash
make check
```

Expected: `ImportError` — `_impl` functions not defined yet.

- [ ] **Step 3: Implement tools.py**

Replace `drummer/api/mcp/tools.py`:

```python
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

from drummer.core.cookies import CookieJar
from drummer.core.engine import send as engine_send
from drummer.core.storage.formats import (
    RequestFile,
    RequestFrontmatter,
    parse_request_file,
    write_request_file,
)
from drummer.core.storage.project import (
    Environment,
    list_environments,
    list_requests,
    load_environment,
    save_environment,
)
from drummer.core.variables import resolve


async def list_requests_impl(project_dir: Path) -> list[dict[str, str]]:
    paths = list_requests(project_dir)
    result = []
    for p in paths:
        rf = parse_request_file(p)
        result.append({
            "path": str(p.relative_to(project_dir)),
            "name": rf.frontmatter.name,
            "method": rf.frontmatter.method,
            "url": rf.frontmatter.url,
        })
    return result


async def get_request_impl(project_dir: Path, path: str) -> dict[str, object]:
    rf = parse_request_file(project_dir / path)
    return rf.frontmatter.model_dump(mode="json")


async def create_request_impl(
    project_dir: Path,
    path: str,
    name: str,
    method: str = "GET",
    url: str = "",
) -> dict[str, str]:
    full_path = project_dir / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    fm = RequestFrontmatter.model_validate({"name": name, "method": method, "url": url})
    write_request_file(RequestFile(frontmatter=fm, body="", path=full_path))
    return {"path": path, "name": name}


async def update_request_impl(
    project_dir: Path,
    path: str,
    **kwargs: object,
) -> dict[str, str]:
    full_path = project_dir / path
    rf = parse_request_file(full_path)
    updated_fm = rf.frontmatter.model_copy(update={k: v for k, v in kwargs.items() if v is not None})
    write_request_file(RequestFile(frontmatter=updated_fm, body=rf.body, path=full_path))
    return {"path": path}


async def send_request_impl(
    project_dir: Path,
    cookie_jar: CookieJar,
    active_environment: str,
    path: str,
    environment: str = "",
    overrides: dict[str, str] | None = None,
) -> dict[str, object]:
    env_name = environment or active_environment
    request_file = parse_request_file(project_dir / path)
    env_path = project_dir / ".drummer" / "environments" / f"{env_name}.yaml"
    env = load_environment(env_path)
    variables: dict[str, str] = {**env.variables, **(overrides or {})}
    resolved = resolve(request_file, variables)
    result = await engine_send(resolved, cookie_jar)
    return {
        "status_code": result.status_code,
        "url": result.url,
        "headers": result.headers,
        "body": result.body,
        "encoding": result.encoding,
        "elapsed_ms": result.elapsed_ms,
        "warnings": result.warnings,
    }


async def get_history_impl(
    db_factory: Any,
    request_path: str = "",
    limit: int = 50,
) -> list[dict[str, object]]:
    from sqlalchemy import select
    from drummer.api.db.models import ResponseHistoryRecord

    async with db_factory() as session:
        stmt = (
            select(ResponseHistoryRecord)
            .order_by(ResponseHistoryRecord.sent_at.desc())
            .limit(limit)
        )
        if request_path:
            stmt = stmt.where(ResponseHistoryRecord.request_path == request_path)
        result = await session.execute(stmt)
        return [r.to_dict() for r in result.scalars().all()]


async def list_environments_impl(project_dir: Path) -> list[dict[str, str]]:
    envs = list_environments(project_dir)
    return [{"name": e.name, "variable_count": str(len(e.variables))} for e in envs]


async def get_environment_impl(project_dir: Path, name: str) -> dict[str, str]:
    env_path = project_dir / ".drummer" / "environments" / f"{name}.yaml"
    env = load_environment(env_path)
    return env.variables


async def set_variable_impl(
    project_dir: Path,
    environment: str,
    key: str,
    value: str,
) -> dict[str, str]:
    env_path = project_dir / ".drummer" / "environments" / f"{environment}.yaml"
    env = load_environment(env_path)
    updated = Environment(name=environment, variables={**env.variables, key: value})
    save_environment(updated, project_dir)
    return {key: value}


async def switch_environment_impl(app_state: Any, name: str) -> dict[str, str]:
    app_state.active_environment = name
    return {"active_environment": name}


async def list_cookies_impl(cookie_jar: CookieJar) -> dict[str, dict[str, str]]:
    return cookie_jar.all_cookies()


async def clear_cookies_impl(cookie_jar: CookieJar) -> dict[str, str]:
    cookie_jar.clear()
    return {"status": "cleared"}


def register_mcp_tools(mcp: FastApiMCP, app: FastAPI) -> None:
    project_dir: Path = app.state.project_dir
    cookie_jar: CookieJar = app.state.cookie_jar
    db_factory = app.state.db_factory

    @mcp.tool()
    async def list_requests_tool() -> list[dict[str, str]]:
        return await list_requests_impl(project_dir)

    @mcp.tool()
    async def get_request_tool(path: str) -> dict[str, object]:
        return await get_request_impl(project_dir, path)

    @mcp.tool()
    async def create_request_tool(
        path: str, name: str, method: str = "GET", url: str = ""
    ) -> dict[str, str]:
        return await create_request_impl(project_dir, path, name, method, url)

    @mcp.tool()
    async def update_request_tool(
        path: str,
        name: str | None = None,
        method: str | None = None,
        url: str | None = None,
    ) -> dict[str, str]:
        updates: dict[str, object] = {}
        if name is not None:
            updates["name"] = name
        if method is not None:
            updates["method"] = method
        if url is not None:
            updates["url"] = url
        return await update_request_impl(project_dir, path, **updates)

    @mcp.tool()
    async def send_request_tool(
        path: str,
        environment: str = "",
        overrides: dict[str, str] | None = None,
    ) -> dict[str, object]:
        active: str = app.state.active_environment
        return await send_request_impl(project_dir, cookie_jar, active, path, environment, overrides)

    @mcp.tool()
    async def get_history_tool(request_path: str = "", limit: int = 50) -> list[dict[str, object]]:
        return await get_history_impl(db_factory, request_path, limit)

    @mcp.tool()
    async def list_environments_tool() -> list[dict[str, str]]:
        return await list_environments_impl(project_dir)

    @mcp.tool()
    async def get_environment_tool(name: str) -> dict[str, str]:
        return await get_environment_impl(project_dir, name)

    @mcp.tool()
    async def set_variable_tool(environment: str, key: str, value: str) -> dict[str, str]:
        return await set_variable_impl(project_dir, environment, key, value)

    @mcp.tool()
    async def switch_environment_tool(name: str) -> dict[str, str]:
        return await switch_environment_impl(app.state, name)

    @mcp.tool()
    async def list_cookies_tool() -> dict[str, dict[str, str]]:
        return await list_cookies_impl(cookie_jar)

    @mcp.tool()
    async def clear_cookies_tool() -> dict[str, str]:
        return await clear_cookies_impl(cookie_jar)
```

- [ ] **Step 4: Run make check**

```bash
make check
```

Expected: All tests pass. If Pyright complains about `Any` in `get_history_impl`, change `db_factory: Any` to:

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
async def get_history_impl(
    db_factory: async_sessionmaker[AsyncSession],
    ...
```

Fix all Pyright errors before committing.

- [ ] **Step 5: Commit**

```bash
git add drummer/api/mcp/tools.py tests/integration/test_mcp_tools.py
git commit -m "feat: implement 12 MCP tools"
```

---

### Task 11: CLI serve command

The `serve` stub in `cli.py` ignores `--project` and doesn't start a real server. Implement it with uvicorn.

**Files:**
- Modify: `drummer/cli.py`

- [ ] **Step 1: Replace the serve stub**

In `drummer/cli.py`, replace the `serve` function:

```python
@app.command()
def serve(
    project: Annotated[str, typer.Option("--project", "-p", help="Path to the project folder.")],
    port: Annotated[int, typer.Option("--port", help="Port to listen on.")] = 8000,
) -> None:
    """Start the Drummer API server for PROJECT."""
    import uvicorn
    from drummer.api.app import create_app

    project_dir = Path(project).expanduser().resolve()
    if not (project_dir / ".drummer" / "project.yaml").exists():
        typer.echo(f"Error: {project_dir} is not a Drummer project (missing .drummer/project.yaml)", err=True)
        raise typer.Exit(code=1)

    application = create_app(project_dir=project_dir)
    typer.echo(f"Drummer serving {project_dir.name} on http://localhost:{port}")
    uvicorn.run(application, host="0.0.0.0", port=port)
```

Also add `from pathlib import Path` to the imports at the top of `cli.py` if not already present.

- [ ] **Step 2: Run make check**

```bash
make check
```

Expected: All tests pass, 0 Pyright errors.

- [ ] **Step 3: Commit**

```bash
git add drummer/cli.py
git commit -m "feat: implement drummer serve command with uvicorn"
```

---

### Task 12: Final make check + TODO update

- [ ] **Step 1: Run the full check suite**

```bash
make check
```

All must pass: ruff, pyright, pytest. Fix any remaining issues before updating TODO.

- [ ] **Step 2: Update TODO.md**

Replace the contents of `TODO.md`:

```markdown
# TODO

Current sprint: **Phase 4 — API + MCP** ✅ Complete

Phase 5 plan not yet written.
```

- [ ] **Step 3: Update ROADMAP.md**

Change Phase 4's status to `✅ Done` and Phase 5 to `⬜ Next`:

```markdown
| 4 — API + MCP | FastAPI app, REST routes, MCP tools, response history | ✅ Done |
| 5 — React UI | Vite scaffold, workspace view, request editor, response viewer | ⬜ Next |
```

- [ ] **Step 4: Final commit**

```bash
git add TODO.md ROADMAP.md
git commit -m "chore: mark Phase 4 API + MCP complete in TODO and ROADMAP"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|-----------------|------|
| `create_app(project_dir, db_url)` factory | Task 4 |
| Per-process in-memory CookieJar singleton | Task 4 |
| `active_environment` in app.state | Task 4 |
| `GET/POST /api/requests`, CRUD | Task 5 |
| `GET/PUT /api/environments` | Task 6 |
| `GET/DELETE /api/cookies` | Task 7 |
| `GET/DELETE /api/history` | Task 8 |
| `POST /api/send` SSE | Task 9 |
| SSE event sequence: status→headers→body→done | Task 9 |
| SSE error event on network failure | Task 9 |
| History written after body, before done | Task 9 |
| No history record on failure | Task 9 |
| 12 MCP tools with direct core calls | Task 10 |
| Fix header-flattening (list[tuple]) | Task 1 |
| `drummer serve --project <dir>` CLI | Task 11 |
| Integration tests with in-memory SQLite + tmp_path | Tasks 4–10 |

**Placeholder scan:** No TBDs or incomplete sections. All code blocks are runnable.

**Type consistency:**
- `RequestResult.headers: list[tuple[str, str]]` — defined in Task 1, used in Task 9 (`json.dumps(result.headers)`)
- `CookieJar.all_cookies() -> dict[str, dict[str, str]]` — defined in Task 7, used in Task 10
- `parse_sse(text: str) -> list[dict[str, object]]` — defined in conftest (Task 4), used in Task 9 tests
- `MockTransport` — defined in conftest (Task 4), imported in Task 9 tests
- `register_mcp_tools(mcp: FastApiMCP, app: FastAPI) -> None` — defined in Task 10, called in Task 4 (app.py)
- `_impl` function signatures in `tools.py` match their test call sites in `test_mcp_tools.py`
