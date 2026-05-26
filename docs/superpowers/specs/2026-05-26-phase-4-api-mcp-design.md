# Phase 4: API + MCP Design

## Overview

Phase 4 adds the FastAPI web layer, REST routes, MCP tools, and SQLite response history on top of the Phase 3 HTTP engine. The server runs in single-project mode: launched with `--project <dir>`, it serves exactly one project for its lifetime.

**Decisions made:**
- CookieJar: per-process singleton (in-memory, resets on restart — new sessions should not assume auth is established)
- `/api/send`: SSE (server-sent events), baked in now rather than retrofitted later
- Network errors: SSE `error` event, stream always closes cleanly
- MCP tools: 12 with backing in Phase 4; scripting and GraphQL tools added in Phases 6 and 8
- Route structure: flat (`/api/requests`, not `/api/projects/{id}/requests`)

---

## File Structure

```
drummer/api/
├── app.py              # create_app(project_dir, db_url) -> FastAPI
├── deps.py             # FastAPI Depends: get_db, get_cookie_jar, get_project_dir
├── db/
│   ├── __init__.py
│   ├── models.py       # SQLAlchemy ORM: ResponseHistoryRecord
│   └── session.py      # async_session_factory, init_db
├── routes/
│   ├── __init__.py
│   ├── requests.py     # /api/requests — CRUD over request files
│   ├── environments.py # /api/environments — read/write env variables
│   ├── send.py         # /api/send — SSE send pipeline
│   ├── history.py      # /api/history — read/delete history
│   └── cookies.py      # /api/cookies — inspect/clear CookieJar
└── mcp/
    ├── __init__.py
    └── tools.py        # 12 MCP tool functions, registered with fastapi-mcp
```

`cli.py` gains a `serve` subcommand: `drummer serve --project <dir> [--port 8000]`.

---

## App Factory

`app.py` exposes a factory function so tests can instantiate with an in-memory SQLite URL:

```python
def create_app(project_dir: Path, db_url: str = "sqlite+aiosqlite:///<default_path>") -> FastAPI:
    app = FastAPI(title="Drummer", lifespan=lifespan)
    app.state.project_dir = project_dir
    app.state.cookie_jar = CookieJar()
    app.state.active_environment = "local"
    app.state.db_factory = async_session_factory(db_url)
    app.include_router(requests_router, prefix="/api")
    app.include_router(environments_router, prefix="/api")
    app.include_router(send_router, prefix="/api")
    app.include_router(history_router, prefix="/api")
    app.include_router(cookies_router, prefix="/api")
    # MCP mounted at /mcp via fastapi-mcp
    return app
```

The default `db_url` resolves to `~/.local/share/drummer/history.db`.

The `lifespan` async context manager runs `init_db()` on startup (creates schema if absent). Nothing on shutdown — the CookieJar is intentionally ephemeral.

### Dependencies (`deps.py`)

Three injectors; route handlers take only what they need:

```python
def get_project_dir(request: Request) -> Path: ...
def get_cookie_jar(request: Request) -> CookieJar: ...
async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]: ...
```

---

## REST Routes

All handlers are thin: receive validated Pydantic input, call `drummer.core.*`, return a Pydantic response model. No business logic in handlers.

### Requests

```
GET    /api/requests              list_requests(project_dir) — name + path summaries
GET    /api/requests/{path:path}  parse_request_file(...)
POST   /api/requests              write_request_file(...) — create
PUT    /api/requests/{path:path}  write_request_file(...) — update
DELETE /api/requests/{path:path}  path.unlink()
```

### Environments

```
GET  /api/environments        list_environments(project_dir)
GET  /api/environments/{name} load_environment(...)
PUT  /api/environments/{name} save_environment(...)
```

### Cookies

```
GET    /api/cookies   cookie_jar.all_cookies()
DELETE /api/cookies   cookie_jar.clear()
```

### History

```
GET    /api/history   newest-first; optional ?limit= and ?request_path= filters
DELETE /api/history   delete all records
```

### Send (SSE)

`POST /api/send` accepts:

```python
class SendRequest(BaseModel):
    path: str
    environment: str = ""          # defaults to app.state.active_environment
    overrides: dict[str, str] = {} # inline variable overrides
```

The handler:
1. Resolves the request via `variables.resolve()`
2. Calls `engine.send(resolved, cookie_jar)` → `RequestResult`
3. Emits `status`, `headers`, `body` events
4. Writes a `ResponseHistoryRecord` to the db
5. Emits `done` with the `history_id`, closes the stream

**SSE event sequence (success):**

```
event: status   data: {"status_code": 200, "url": "https://..."}
event: headers  data: {"content-type": "application/json", ...}
event: body     data: {"body": "...", "encoding": "utf-8", "elapsed_ms": 42.1}
event: done     data: {"history_id": "<uuid>"}
```

**SSE event sequence (network failure):**

```
event: error    data: {"message": "Connection refused: ..."}
```

The stream always closes cleanly after `done` or `error`. No history record is written on failure.

**MCP `send_request`** calls the same core functions directly and returns the full `RequestResult` as JSON — no SSE for LLM consumers.

---

## Response History

One SQLAlchemy ORM table:

```python
class ResponseHistoryRecord(Base):
    __tablename__ = "response_history"

    id: Mapped[str]              # UUID, primary key
    sent_at: Mapped[datetime]    # UTC
    request_path: Mapped[str]    # relative path to .md file
    request_name: Mapped[str]
    environment: Mapped[str]
    method: Mapped[str]
    url: Mapped[str]
    status_code: Mapped[int]
    elapsed_ms: Mapped[float]
    request_headers: Mapped[str]   # JSON list[tuple[str, str]]
    request_body: Mapped[str]
    response_headers: Mapped[str]  # JSON list[tuple[str, str]]
    response_body: Mapped[str]
    encoding: Mapped[str]
    warnings: Mapped[str]          # JSON list[str]
```

Headers are stored as `list[tuple[str, str]]` (JSON-encoded) to preserve duplicate header names (e.g. multiple `Set-Cookie` values). This also fixes the known header-flattening issue in `engine.py` where `dict(response.headers)` collapsed duplicates — fix by using `list(response.headers.multi_items())` instead, and update `RequestResult.headers` from `dict[str, str]` to `list[tuple[str, str]]`.

`init_db()` runs `Base.metadata.create_all()` on startup. No migrations in Phase 4.

---

## MCP Tools

Twelve tools in `api/mcp/tools.py`, registered with fastapi-mcp at `/mcp`. All call `drummer.core.*` directly — no HTTP round-trip through REST routes. Tools that need the db receive an injected `AsyncSession` via fastapi-mcp's FastAPI-style dependency injection.

| Tool | Core call | Notes |
|------|-----------|-------|
| `list_requests` | `storage.project.list_requests()` | Name + path summaries |
| `get_request` | `storage.formats.parse_request_file()` | Full frontmatter + body |
| `create_request` | `storage.formats.write_request_file()` | Creates file on disk |
| `update_request` | `storage.formats.write_request_file()` | Overwrites existing |
| `send_request` | `variables.resolve()` + `engine.send()` | Returns `RequestResult` as JSON |
| `get_history` | SQLAlchemy query | Optional `request_path`, `limit` |
| `list_environments` | `storage.project.list_environments()` | Names + variable counts |
| `get_environment` | `storage.project.load_environment()` | Full variable dict |
| `set_variable` | `load_environment()` + `save_environment()` | Upserts one key |
| `switch_environment` | Updates `app.state.active_environment` | In-memory only |
| `list_cookies` | `cookie_jar.all_cookies()` | Hostname-scoped |
| `clear_cookies` | `cookie_jar.clear()` | Wipes in-memory jar |

Scripting tools (`run_pre_script`, `run_post_script`) added in Phase 6. GraphQL tools added in Phase 8.

---

## Testing

### Unit tests (`tests/unit/`)
- `test_db_models.py` — ORM model construction, JSON serialisation of headers/warnings
- `test_deps.py` — dependency functions with a mock `Request` object

### Integration tests (`tests/integration/`)

Use FastAPI's `AsyncClient` + `httpx.ASGITransport` against a real `create_app()` instance with `"sqlite+aiosqlite:///:memory:"` and a `tmp_path` project dir. Network calls use a mock `httpx.AsyncBaseTransport` (same pattern as Phase 3).

**Key scenarios:**
- Request CRUD round-trip (create → get → update → delete)
- Environment read/write
- `/api/send` happy path — SSE stream parses to correct event sequence, history record written
- `/api/send` network failure — `error` event emitted, no history record written
- `/api/send` with variable overrides
- Cookie jar: SESSION mode updates jar after send, DISABLED mode does not
- History: newest-first ordering, `?request_path=` filter, `DELETE /api/history` clears all
- MCP `send_request` returns full JSON result

The `create_app()` factory is the test seam — every test starts with a clean db and project dir.
