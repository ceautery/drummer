# Phase 18 — Agent-ergonomic send Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give agents a clean JSON `POST /api/agent/send` MCP tool that sends a saved request and returns one structured result, with dry-run, JSONPath field extraction, and body truncation to keep an agent's context window from flooding.

**Architecture:** A new FastAPI route (`drummer/api/routes/agent.py`) reusing the SSE route's core path (`parse_request_file` → `load_environment` → `resolve()` → `engine.send`) but returning a single `AgentSendResult` Pydantic object. Two pure, web-free core helpers (`extract_jsonpath`, `truncate_body`) in `drummer/core/agent_shaping.py`. `FastApiMCP(app)` mirrors the route as an MCP tool automatically.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest + httpx; new dep `jsonpath-ng`.

**Critical process notes:**
- ruff `select = ["ALL"]` — **no blind `except Exception`** (BLE001). Catch the specific jsonpath-ng exception classes (see Task 1).
- pyright is **strict** with `stubPath: stubs`; `jsonpath-ng` is untyped, so it needs **stub files** under `stubs/jsonpath_ng/` (no `# type: ignore`).
- No suppression comments anywhere. `make check` must pass before each commit.
- End commit messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## File Structure
- Modify `pyproject.toml` — add `jsonpath-ng` dependency (Task 1).
- Create `stubs/jsonpath_ng/__init__.pyi`, `stubs/jsonpath_ng/ext/__init__.pyi`, `stubs/jsonpath_ng/exceptions/__init__.pyi` (Task 1).
- Create `drummer/core/agent_shaping.py` + `tests/unit/test_agent_shaping.py` (Task 1).
- Create `drummer/api/routes/agent.py`; modify `drummer/api/app.py` (register router); create `tests/integration/test_agent_route.py` (Task 2).
- Modify `ROADMAP.md`, `TODO.md` (Task 3).

Ordering: Task 1 (helpers, independently green) → Task 2 (route, depends on Task 1) → Task 3 (gate/verify/docs).

---

## Task 1: Dependency, stubs, and core shaping helpers

**Files:**
- Modify: `pyproject.toml`
- Create: `stubs/jsonpath_ng/__init__.pyi`, `stubs/jsonpath_ng/ext/__init__.pyi`, `stubs/jsonpath_ng/exceptions/__init__.pyi`
- Create: `drummer/core/agent_shaping.py`
- Test: `tests/unit/test_agent_shaping.py`

- [ ] **Step 1: Add the dependency and install it.**

In `pyproject.toml`, add to the `dependencies` list (keep alphabetical-ish with the others):
```
    "jsonpath-ng>=1.6",
```
Then install into the venv: `venv/bin/pip install "jsonpath-ng>=1.6"`.

- [ ] **Step 2: Discover the exact exception classes** (needed for a non-blind except under ruff ALL):

Run: `venv/bin/python -c "import jsonpath_ng.exceptions as e; print([n for n in dir(e) if n[0].isupper()])"`
Note the class names (expected: `JsonPathParserError`, and a lexer error such as `JsonPathLexerError`). Use the actual names you see in the stub and the helper.

- [ ] **Step 3: Write the stubs.**

`stubs/jsonpath_ng/__init__.pyi`:
```python
from typing import Any

class DatumInContext:
    value: Any

class JSONPath:
    def find(self, data: Any) -> list[DatumInContext]: ...

def parse(path: str) -> JSONPath: ...
```

`stubs/jsonpath_ng/ext/__init__.pyi`:
```python
from jsonpath_ng import JSONPath

def parse(path: str) -> JSONPath: ...
```

`stubs/jsonpath_ng/exceptions/__init__.pyi` (use the real class names from Step 2):
```python
class JsonPathParserError(Exception): ...
class JsonPathLexerError(Exception): ...
```

- [ ] **Step 4: Write the failing unit tests.** Create `tests/unit/test_agent_shaping.py`:

```python
from drummer.core.agent_shaping import extract_jsonpath, truncate_body


def test_extract_jsonpath_matches() -> None:
    matches, err = extract_jsonpath('{"data": {"items": [{"name": "a"}, {"name": "b"}]}}', "$.data.items[*].name")
    assert err is None
    assert matches == ["a", "b"]


def test_extract_jsonpath_no_match_returns_empty() -> None:
    matches, err = extract_jsonpath('{"a": 1}', "$.nope")
    assert err is None
    assert matches == []


def test_extract_jsonpath_non_json_returns_error() -> None:
    matches, err = extract_jsonpath("not json", "$.a")
    assert matches is None
    assert err is not None


def test_extract_jsonpath_invalid_expression_returns_error() -> None:
    matches, err = extract_jsonpath('{"a": 1}', "$$$bad$$$")
    assert matches is None
    assert err is not None


def test_truncate_body_under_threshold() -> None:
    text, truncated, total = truncate_body("hello", 100)
    assert text == "hello"
    assert truncated is False
    assert total == 5


def test_truncate_body_over_threshold() -> None:
    text, truncated, total = truncate_body("hello world", 5)
    assert text == "hello"
    assert truncated is True
    assert total == 11


def test_truncate_body_none_means_full() -> None:
    text, truncated, total = truncate_body("hello world", None)
    assert text == "hello world"
    assert truncated is False
    assert total == 11
```

- [ ] **Step 5: Run — expect FAIL** (module missing): `venv/bin/pytest tests/unit/test_agent_shaping.py -v`

- [ ] **Step 6: Implement** `drummer/core/agent_shaping.py`:

```python
import json

from jsonpath_ng.exceptions import JsonPathLexerError, JsonPathParserError
from jsonpath_ng.ext import parse as jsonpath_parse


def extract_jsonpath(body_text: str, expr: str) -> tuple[list[object] | None, str | None]:
    try:
        data = json.loads(body_text)
    except ValueError:
        return None, "response body is not valid JSON"
    try:
        expression = jsonpath_parse(expr)
    except (JsonPathParserError, JsonPathLexerError) as exc:
        return None, f"invalid JSONPath expression: {exc}"
    return [match.value for match in expression.find(data)], None


def truncate_body(body: str, max_chars: int | None) -> tuple[str, bool, int]:
    total = len(body)
    if max_chars is None or total <= max_chars:
        return body, False, total
    return body[:max_chars], True, total
```

> If Step 5's `test_extract_jsonpath_invalid_expression_returns_error` still errors (uncaught exception) because jsonpath-ng raised a class not in the `except` tuple, add that exact class (from the traceback) to both the `except` tuple and the exceptions stub. Do NOT use a blind `except Exception` (ruff BLE001).

- [ ] **Step 7: Run — expect PASS:** `venv/bin/pytest tests/unit/test_agent_shaping.py -v`

- [ ] **Step 8: Lint + commit.** `venv/bin/ruff check drummer tests stubs && venv/bin/ruff format --check . && venv/bin/pyright drummer`

```bash
git add pyproject.toml stubs/jsonpath_ng drummer/core/agent_shaping.py tests/unit/test_agent_shaping.py
git commit -m "feat(core): jsonpath extraction + body truncation helpers for agent send (18)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: The `POST /api/agent/send` route

**Files:**
- Create: `drummer/api/routes/agent.py`
- Modify: `drummer/api/app.py`
- Test: `tests/integration/test_agent_route.py`

**Context:** Mirror `drummer/api/routes/send.py`'s resolve+send+history logic, but non-streaming. The engine's `RequestResult` has `sent` (a `SentRequest`), `warnings`, `variables` (Phase 17). `SentRequest` is `from drummer.core.engine import SentRequest`. The integration conftest provides `client_with_mock` (mock transport → 200 `{"ok": true}`) and a `project_dir` fixture (a tmp project with a `local` env). The history list is available at `GET /api/history`. `ResponseHistoryRecord` columns: id, sent_at, request_path, request_name, environment, method, url, status_code, elapsed_ms, request_headers, request_body, response_headers, response_body, encoding, warnings.

- [ ] **Step 1: Write the failing integration tests.** Create `tests/integration/test_agent_route.py`. Write request files directly into `project_dir` (mirror how `test_send_route.py` seeds requests; that file shows the exact app/client construction — reuse `client_with_mock` + `project_dir`):

```python
from http import HTTPStatus
from pathlib import Path

from httpx import AsyncClient


def _write_request(project_dir: Path, name: str, body: str) -> None:
    (project_dir / name).write_text(body, encoding="utf-8")


async def test_agent_send_returns_structured_result(client_with_mock: AsyncClient, project_dir: Path) -> None:
    _write_request(project_dir, "r.md", '---\nname: R\nmethod: GET\nurl: "https://api.test/x"\n---\n')
    resp = await client_with_mock.post("/api/agent/send", json={"path": "r.md"})
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["dry_run"] is False
    assert data["status_code"] == HTTPStatus.OK
    assert data["sent"]["method"] == "GET"
    assert data["sent"]["url"] == "https://api.test/x"
    assert data["body_total_chars"] > 0


async def test_agent_send_dry_run_does_not_send_or_record(client_with_mock: AsyncClient, project_dir: Path) -> None:
    _write_request(
        project_dir, "d.md", '---\nname: D\nmethod: GET\nurl: "{{base_url}}/x"\n---\n'
    )
    resp = await client_with_mock.post(
        "/api/agent/send",
        json={"path": "d.md", "dry_run": True, "overrides": {"base_url": "https://sub.example"}},
    )
    data = resp.json()
    assert data["dry_run"] is True
    assert data["status_code"] is None
    assert data["sent"]["url"] == "https://sub.example/x"
    assert data["body"] is None
    # No history row written for a dry run.
    history = (await client_with_mock.get("/api/history")).json()
    assert history == [] or all(h["request_path"] != "d.md" for h in history)


async def test_agent_send_extract_returns_value_and_omits_body(client_with_mock: AsyncClient, project_dir: Path) -> None:
    # mock transport returns {"ok": true}
    _write_request(project_dir, "e.md", '---\nname: E\nmethod: GET\nurl: "https://api.test/x"\n---\n')
    resp = await client_with_mock.post("/api/agent/send", json={"path": "e.md", "extract": "$.ok"})
    data = resp.json()
    assert data["extracted"] == [True]
    assert data["extract_error"] is None
    assert data["body"] is None


async def test_agent_send_extract_error_keeps_body(client_with_mock: AsyncClient, project_dir: Path) -> None:
    _write_request(project_dir, "e2.md", '---\nname: E2\nmethod: GET\nurl: "https://api.test/x"\n---\n')
    resp = await client_with_mock.post("/api/agent/send", json={"path": "e2.md", "extract": "$$$bad$$$"})
    data = resp.json()
    assert data["extracted"] is None
    assert data["extract_error"] is not None
    assert data["body"] is not None


async def test_agent_send_truncates_body(client_with_mock: AsyncClient, project_dir: Path) -> None:
    _write_request(project_dir, "t.md", '---\nname: T\nmethod: GET\nurl: "https://api.test/x"\n---\n')
    resp = await client_with_mock.post("/api/agent/send", json={"path": "t.md", "max_body_chars": 3})
    data = resp.json()
    assert data["body_truncated"] is True
    assert len(data["body"]) == 3
    assert data["body_total_chars"] > 3


async def test_agent_send_surfaces_unresolved_warnings(client_with_mock: AsyncClient, project_dir: Path) -> None:
    _write_request(project_dir, "w.md", '---\nname: W\nmethod: GET\nurl: "https://api.test/{{missing}}"\n---\n')
    resp = await client_with_mock.post("/api/agent/send", json={"path": "w.md"})
    data = resp.json()
    assert "missing" in data["warnings"]


async def test_agent_send_missing_request_404(client_with_mock: AsyncClient) -> None:
    resp = await client_with_mock.post("/api/agent/send", json={"path": "nope.md"})
    assert resp.status_code == HTTPStatus.NOT_FOUND
```

(If `client_with_mock`/`project_dir` are not directly importable as fixtures the way other integration tests use them, mirror the exact construction `test_send_route.py` uses — that file is the reference for app + mock transport + history setup.)

- [ ] **Step 2: Run — expect FAIL** (route 404/not registered): `venv/bin/pytest tests/integration/test_agent_route.py -v`

- [ ] **Step 3: Implement the route.** Create `drummer/api/routes/agent.py`:

```python
import json
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, cast
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drummer.api.db.models import ResponseHistoryRecord
from drummer.api.deps import get_cookie_jar, get_oauth_cache, get_project_dir
from drummer.core.agent_shaping import extract_jsonpath, truncate_body
from drummer.core.cookies import CookieJar
from drummer.core.engine import SentRequest
from drummer.core.engine import send as engine_send
from drummer.core.oauth import OAuthError, OAuthTokenCache
from drummer.core.storage.formats import parse_request_file
from drummer.core.storage.project import load_environment, load_project
from drummer.core.variables import resolve

router = APIRouter()

ProjectDir = Annotated[Path, Depends(get_project_dir)]
CookieJarDep = Annotated[CookieJar, Depends(get_cookie_jar)]
OAuthCacheDep = Annotated[OAuthTokenCache, Depends(get_oauth_cache)]


def _safe_path(project_dir: Path, user_path: str) -> Path:
    full = (project_dir / user_path).resolve()
    if not full.is_relative_to(project_dir.resolve()):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Invalid path: outside project directory"
        )
    return full


class AgentSendBody(BaseModel):
    path: str
    environment: str = ""
    overrides: dict[str, str] = Field(default_factory=dict)
    dry_run: bool = False
    extract: str | None = None
    max_body_chars: int | None = 2048


class AgentSendResult(BaseModel):
    dry_run: bool
    status_code: int | None
    url: str
    headers: list[tuple[str, str]] = Field(default_factory=list)
    elapsed_ms: float | None
    encoding: str | None
    sent: SentRequest | None
    warnings: list[str] = Field(default_factory=list)
    variables: dict[str, str] = Field(default_factory=dict)
    body: str | None
    body_truncated: bool = False
    body_total_chars: int = 0
    extracted: list[object] | None = None
    extract_error: str | None = None


@router.post("/agent/send", operation_id="agent_send")
async def agent_send_route(
    body: AgentSendBody,
    request: Request,
    project_dir: ProjectDir,
    cookie_jar: CookieJarDep,
    oauth_cache: OAuthCacheDep,
) -> AgentSendResult:
    environment = body.environment or cast("str", request.app.state.active_environment)
    transport = cast("httpx.AsyncBaseTransport | None", request.app.state.transport)

    req_path = _safe_path(project_dir, body.path)
    if not req_path.exists():
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Request not found: {body.path}")
    request_file = parse_request_file(req_path)

    env_path = project_dir / ".drummer" / "environments" / f"{environment}.yaml"
    env = load_environment(env_path) if env_path.exists() else None
    variables: dict[str, str] = {**(env.variables if env else {}), **body.overrides}

    project_timeout_ms: int | None = None
    try:
        project_timeout_ms = load_project(project_dir).script_timeout_ms
    except (OSError, ValueError):
        pass

    resolved = resolve(request_file, variables, project_timeout_ms=project_timeout_ms)

    if body.dry_run:
        return AgentSendResult(
            dry_run=True,
            status_code=None,
            url=resolved.url,
            headers=[],
            elapsed_ms=None,
            encoding=None,
            sent=SentRequest(
                method=resolved.method,
                url=resolved.url,
                params=resolved.params,
                headers=resolved.headers,
                body=resolved.body,
            ),
            warnings=resolved.warnings,
            variables=dict(variables),
            body=None,
        )

    try:
        result = await engine_send(
            resolved, cookie_jar, oauth_cache=oauth_cache, transport=transport
        )
    except (httpx.HTTPError, OAuthError) as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_GATEWAY, detail=f"Request failed: {exc}"
        ) from exc

    extracted: list[object] | None = None
    extract_error: str | None = None
    out_body: str | None
    truncated = False
    total_chars = len(result.body)

    if body.extract is not None:
        matches, err = extract_jsonpath(result.body, body.extract)
        if err is not None:
            extract_error = err
            out_body, truncated, total_chars = truncate_body(result.body, body.max_body_chars)
        else:
            extracted = matches
            out_body = None
    else:
        out_body, truncated, total_chars = truncate_body(result.body, body.max_body_chars)

    if not (result.script_error and result.status_code == 0):
        db_factory = cast("async_sessionmaker[AsyncSession]", request.app.state.db_factory)
        async with db_factory() as session:
            session.add(
                ResponseHistoryRecord(
                    id=str(uuid4()),
                    sent_at=datetime.now(UTC),
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
            )
            await session.commit()

    return AgentSendResult(
        dry_run=False,
        status_code=result.status_code,
        url=result.url,
        headers=result.headers,
        elapsed_ms=result.elapsed_ms,
        encoding=result.encoding,
        sent=result.sent,
        warnings=result.warnings,
        variables=result.variables,
        body=out_body,
        body_truncated=truncated,
        body_total_chars=total_chars,
        extracted=extracted,
        extract_error=extract_error,
    )
```

- [ ] **Step 4: Register the router** in `drummer/api/app.py`. Add the import next to the other route imports:
```python
from drummer.api.routes import agent as agent_routes
```
and the include next to the other `/api` routers (e.g. after the `send_routes` line):
```python
    app.include_router(agent_routes.router, prefix="/api")
```

- [ ] **Step 5: Run — expect PASS:** `venv/bin/pytest tests/integration/test_agent_route.py -v`

- [ ] **Step 6: Lint + full check + commit.** `venv/bin/ruff check drummer tests && venv/bin/ruff format --check . && venv/bin/pyright drummer`, then `make check`.

```bash
git add drummer/api/routes/agent.py drummer/api/app.py tests/integration/test_agent_route.py
git commit -m "feat(api): POST /agent/send — JSON send with dry-run, extract, truncation (18)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Gate, verify, docs

**Files:** `ROADMAP.md`, `TODO.md`

- [ ] **Step 1: Full gate.** `make check` → green (this includes pyright with the new stubs and the full pytest suite). Fix anything red at the root.

- [ ] **Step 2: Manual verification (JSON endpoint — no browser needed).** Build is not required (no frontend change). Start the server against a temp project containing a request whose URL uses a `{{var}}`, then exercise the new tool with curl:
  - `dry_run: true` → returns `sent` with the substituted URL, `status_code: null`, and no history row.
  - a real send → `status_code`, `sent`, `warnings`, a (truncated) `body`.
  - `extract: "$.<field>"` against a JSON response → `extracted` populated, `body: null`.
  - `max_body_chars: 3` → `body_truncated: true`, `body_total_chars` == full length.
  Capture the JSON outputs as evidence. Stop the server and remove temp dirs when done.

- [ ] **Step 3: Docs.** In `ROADMAP.md`, change the Phase 18 row status to `✅ Done (verified)`. In `TODO.md`, move Phase 18 to a done note and mark it the first sub-phase of the Agent API Toolkit arc; leave Phases 19–21 as next.

- [ ] **Step 4: Commit.**
```bash
git add ROADMAP.md TODO.md
git commit -m "docs: close out Phase 18 (agent-ergonomic send)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage:**
  - New JSON `POST /api/agent/send` route reusing the resolve→engine path → Task 2. ✓
  - jsonpath-ng extraction + truncation as pure core helpers → Task 1. ✓
  - dry_run (resolved `sent`, no send, no OAuth, no history) → Task 2 (`if body.dry_run`) + test. ✓
  - extract omits body on success, keeps body + `extract_error` on failure → Task 2 + two tests. ✓
  - truncation with `max_body_chars` (null = full) → Task 2 + test. ✓
  - real send persists history (parity), dry-run doesn't → Task 2 + dry-run test asserts no row. ✓
  - `sent` returns real (unmasked) values → Task 2 returns `result.sent` as-is. ✓
  - MCP exposure via fastapi-mcp + explicit `operation_id` → Task 2. ✓
- **Placeholder scan:** The only deferred specifics are the exact jsonpath-ng exception class names (Task 1 Step 2 discovers them; Step 6 note handles a surprise class) — driven by a real test, not a placeholder. All code blocks are complete.
- **Type consistency:** `AgentSendResult`/`AgentSendBody` field names match the spec and the tests (`dry_run`, `status_code`, `sent`, `body`, `body_truncated`, `body_total_chars`, `extracted`, `extract_error`). `extract_jsonpath(body_text, expr) -> (list|None, str|None)` and `truncate_body(body, max_chars) -> (str, bool, int)` signatures match their call sites in the route. `SentRequest` reused from the engine for both dry-run and the result.
