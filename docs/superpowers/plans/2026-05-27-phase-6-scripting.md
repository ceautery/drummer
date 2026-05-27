# Phase 6: Scripting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pre/post request JavaScript scripting via QuickJS — `dm` API, script debugger, configurable timeouts, and a ScriptTab UI with editor + output panel.

**Architecture:** Option A — the engine handles script execution directly. `engine.send()` runs the pre-script (applying mutations to the resolved request), sends HTTP, then runs the post-script. Script output travels via `RequestResult` fields through the existing SSE `done` event to the frontend. Zustand `responseStore` holds script output; `ScriptTab` shows editor + output panel.

**Tech Stack:** `quickjs` (already installed), Python `hmac`/`hashlib`, CodeMirror 6 + `@codemirror/lang-javascript`, React 19, Zustand 5.

---

### File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `typings/quickjs.pyi` | Type stub so pyright can check `scripting.py` |
| Create | `drummer/core/debugger.py` | Pattern-matching error → actionable suggestion |
| Create | `drummer/core/scripting.py` | QuickJS runner, `dm` object, `ScriptResult` |
| Modify | `drummer/core/storage/formats.py` | Add `script_timeout_ms` to `RequestFrontmatter` |
| Modify | `drummer/core/storage/project.py` | Add `script_timeout_ms` to `ProjectMeta` |
| Modify | `drummer/core/variables.py` | Copy script fields + `variables` dict into `ResolvedRequest` |
| Modify | `drummer/core/engine.py` | Add script fields to models; wire pre/post script into send pipeline |
| Modify | `drummer/api/routes/send.py` | Load project config for timeout; add script output to `done` event |
| Modify | `pyproject.toml` | Add `[tool.pyright] stubPath = "typings"` |
| Modify | `frontend/src/types.ts` | Add `script_timeout_ms`; add script output fields |
| Modify | `frontend/src/store/responseStore.ts` | Add `scriptLogs`, `scriptError`, `scriptSuggestion` |
| Modify | `frontend/src/store/requestStore.ts` | No change needed — `patch()` already handles arbitrary frontmatter fields |
| Modify | `frontend/src/components/request/ScriptTab.tsx` | Replace stub with editor + sub-tab + output panel |
| Modify | `frontend/src/components/response/ScriptOutput.tsx` | Replace stub with log/error/suggestion display |
| Create | `tests/unit/test_debugger.py` | Unit tests for debugger pattern registry |
| Create | `tests/unit/test_scripting.py` | Unit tests for scripting layer |

---

### Task 1: Storage layer — `script_timeout_ms` field

**Files:**
- Modify: `drummer/core/storage/formats.py`
- Modify: `drummer/core/storage/project.py`
- Modify: `tests/unit/test_formats.py`
- Modify: `tests/unit/test_project.py`

- [ ] **Step 1: Add `script_timeout_ms` to `RequestFrontmatter`**

In `drummer/core/storage/formats.py`, add one field to `RequestFrontmatter` after `post_script`:

```python
class RequestFrontmatter(BaseModel):
    name: str
    method: HttpMethod = "GET"
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    encoding: str = "utf-8"
    cookies: CookieConfig = Field(default_factory=CookieConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    graphql: GraphQLConfig | None = None
    pre_script: str = ""
    post_script: str = ""
    script_timeout_ms: int | None = None
    tags: list[str] = Field(default_factory=list)
    skip: bool = False
```

- [ ] **Step 2: Add `script_timeout_ms` to `ProjectMeta`**

In `drummer/core/storage/project.py`, add one field to `ProjectMeta`:

```python
class ProjectMeta(BaseModel):
    name: str
    version: str = "1"
    default_environment: str = "local"
    script_timeout_ms: int | None = None
```

- [ ] **Step 3: Write failing tests**

Add to `tests/unit/test_formats.py`:

```python
def test_request_frontmatter_default_script_timeout_is_none() -> None:
    fm = RequestFrontmatter(name="Test")
    assert fm.script_timeout_ms is None


def test_request_frontmatter_parses_script_timeout(tmp_path: Path) -> None:
    (tmp_path / "req.md").write_text(
        "---\nname: T\nmethod: GET\nurl: http://x.com\nscript_timeout_ms: 10000\n---\n",
        encoding="utf-8",
    )
    rf = parse_request_file(tmp_path / "req.md")
    assert rf.frontmatter.script_timeout_ms == 10000
```

Add to `tests/unit/test_project.py`:

```python
def test_project_meta_default_script_timeout_is_none() -> None:
    meta = ProjectMeta(name="Test")
    assert meta.script_timeout_ms is None


def test_load_project_parses_script_timeout(tmp_path: Path) -> None:
    (tmp_path / ".drummer").mkdir()
    (tmp_path / ".drummer" / "project.yaml").write_text(
        "name: Test\nscript_timeout_ms: 30000\n", encoding="utf-8"
    )
    meta = load_project(tmp_path)
    assert meta.script_timeout_ms == 30000
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
pytest tests/unit/test_formats.py tests/unit/test_project.py -v
```

Expected: The new tests FAIL (fields don't exist yet).

- [ ] **Step 5: Verify the fields are now parseable**

```bash
pytest tests/unit/test_formats.py tests/unit/test_project.py -v
```

Expected: All tests PASS (fields default to `None`, YAML with `script_timeout_ms` parses correctly).

- [ ] **Step 6: Run full check**

```bash
make check
```

Expected: All pass.

- [ ] **Step 7: Commit**

```bash
git add drummer/core/storage/formats.py drummer/core/storage/project.py \
        tests/unit/test_formats.py tests/unit/test_project.py
git commit -m "feat: add script_timeout_ms to RequestFrontmatter and ProjectMeta"
```

---

### Task 2: Script debugger

**Files:**
- Create: `drummer/core/debugger.py`
- Create: `tests/unit/test_debugger.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_debugger.py`:

```python
from drummer.core.debugger import suggest


def test_undefined_not_object_suggests_json_check() -> None:
    result = suggest("TypeError: undefined is not an object")
    assert result is not None
    assert "JSON" in result or "Content-Type" in result


def test_timeout_suggests_infinite_loop() -> None:
    result = suggest("InternalError: interrupted")
    assert result is not None
    assert "timed out" in result.lower()


def test_syntax_error_returns_suggestion() -> None:
    result = suggest("SyntaxError: expecting ';'\n    at <input>:3")
    assert result is not None


def test_uncaught_exception_returns_suggestion() -> None:
    result = suggest("ReferenceError: foo is not defined\n    at <eval>")
    assert result is not None


def test_unrecognised_error_returns_none() -> None:
    result = suggest("some completely unknown error message xyz")
    assert result is None


def test_dm_response_in_prescript_suggests_move_to_post() -> None:
    result = suggest("dm.response is not available in pre-scripts")
    assert result is not None
    assert "post-script" in result.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_debugger.py -v
```

Expected: `ImportError` — `drummer.core.debugger` does not exist yet.

- [ ] **Step 3: Implement `debugger.py`**

Create `drummer/core/debugger.py`:

```python
import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"dm\.response is not available in pre-scripts", re.IGNORECASE),
        "dm.response is not available in pre-scripts — move this logic to a post-script.",
    ),
    (
        re.compile(r"dm\.request.*mutations.*ignored.*post", re.IGNORECASE),
        "dm.request mutations are ignored in post-scripts — move this logic to a pre-script.",
    ),
    (
        re.compile(r"TypeError.*undefined.*not.*object", re.IGNORECASE),
        "Response may not be JSON — check Content-Type. Try dm.response.text() first.",
    ),
    (
        re.compile(r"InternalError: interrupted"),
        "Script timed out. Check for infinite loops or expensive operations.",
    ),
    (
        re.compile(r"SyntaxError"),
        "Syntax error in script — check for missing brackets, quotes, or semicolons.",
    ),
    (
        re.compile(r".+"),  # catch-all: any non-empty error gets the stack trace shown
        None,  # type: ignore[assignment]  # sentinel — caller shows raw error
    ),
]

_SENTINEL = object()


def suggest(error: str) -> str | None:
    for pattern, message in _PATTERNS[:-1]:
        if pattern.search(error):
            return message
    return None
```

Wait — the catch-all pattern with `None` is awkward. Simplify: just return `None` for unrecognised errors. The raw error is always shown in the UI regardless. Remove the catch-all:

```python
import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"dm\.response is not available in pre-scripts", re.IGNORECASE),
        "dm.response is not available in pre-scripts — move this logic to a post-script.",
    ),
    (
        re.compile(r"TypeError.*undefined.*not.*object", re.IGNORECASE),
        "Response may not be JSON — check Content-Type. Try dm.response.text() first.",
    ),
    (
        re.compile(r"InternalError: interrupted"),
        "Script timed out. Check for infinite loops or expensive operations.",
    ),
    (
        re.compile(r"SyntaxError"),
        "Syntax error in script — check for missing brackets, quotes, or semicolons.",
    ),
    (
        re.compile(r"ReferenceError|TypeError"),
        "Uncaught exception — check the stack trace above for the error location.",
    ),
]


def suggest(error: str) -> str | None:
    for pattern, message in _PATTERNS:
        if pattern.search(error):
            return message
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_debugger.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Run full check**

```bash
make check
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add drummer/core/debugger.py tests/unit/test_debugger.py
git commit -m "feat: add script debugger with pattern-matching error suggestions"
```

---

### Task 3: QuickJS type stub + scripting core

**Files:**
- Create: `typings/quickjs.pyi`
- Modify: `pyproject.toml`
- Create: `drummer/core/scripting.py`
- Create: `tests/unit/test_scripting.py`

- [ ] **Step 1: Create QuickJS type stub**

Create `typings/quickjs.pyi`:

```python
from typing import Any, Callable

class JSException(Exception): ...

class Context:
    def eval(self, code: str) -> Any: ...
    def set(self, name: str, value: Any) -> None: ...
    def get(self, name: str) -> Any: ...
    def add_callable(self, name: str, fn: Callable[..., Any]) -> None: ...
    def parse_json(self, json_str: str) -> Any: ...
    def set_time_limit(self, seconds: float) -> None: ...
    def set_memory_limit(self, limit: int) -> None: ...
    def set_max_stack_size(self, limit: int) -> None: ...
    def gc(self) -> None: ...
```

Add pyright stub path to `pyproject.toml` (append after the existing `[tool.ruff.format]` section):

```toml
[tool.pyright]
stubPath = "typings"
```

- [ ] **Step 2: Write failing tests**

Create `tests/unit/test_scripting.py`:

```python
import hashlib
import hmac
from pathlib import Path

import pytest

from drummer.core.scripting import ScriptResult, run_script

_REQ: dict[str, object] = {
    "url": "http://example.com/api",
    "method": "GET",
    "headers": {},
    "params": {},
    "body": "",
}


def test_console_log_captured() -> None:
    result = run_script(
        "dm.console.log('hello', 'world');",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.logs == ["hello world"]
    assert result.error is None


def test_env_get_returns_variable() -> None:
    result = run_script(
        "dm.console.log(dm.env.get('token'));",
        variables={"token": "abc123"},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.logs == ["abc123"]


def test_env_set_captured_in_mutations() -> None:
    result = run_script(
        "dm.env.set('token', 'newvalue');",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.env_mutations == {"token": "newvalue"}
    assert result.error is None


def test_env_set_visible_to_subsequent_get() -> None:
    result = run_script(
        "dm.env.set('x', '42'); dm.console.log(dm.env.get('x'));",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.logs == ["42"]


def test_request_header_mutation() -> None:
    result = run_script(
        "dm.request.headers['X-Custom'] = 'test-value';",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.request_mutations["headers"]["X-Custom"] == "test-value"
    assert result.error is None


def test_request_url_mutation() -> None:
    result = run_script(
        "dm.request.url = 'http://other.com/api';",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.request_mutations["url"] == "http://other.com/api"


def test_timeout_returns_error() -> None:
    result = run_script(
        "while(true) {}",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
        timeout_ms=100,
    )
    assert result.error is not None
    assert "interrupted" in result.error.lower() or "timed" in (result.suggestion or "").lower()


def test_syntax_error_captured() -> None:
    result = run_script(
        "this is not valid JS !!!",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.error is not None
    assert "SyntaxError" in result.error


def test_dm_response_in_pre_script_raises_error() -> None:
    result = run_script(
        "dm.response.status;",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.error is not None
    assert "pre-script" in result.error.lower()


def test_post_script_can_read_response_status() -> None:
    result = run_script(
        "dm.env.set('code', String(dm.response.status));",
        variables={},
        request_fields=dict(_REQ),
        response_fields={"status": 201, "headers": {}, "body": "{}"},
    )
    assert result.env_mutations == {"code": "201"}
    assert result.error is None


def test_post_script_response_json() -> None:
    result = run_script(
        "var body = dm.response.json(); dm.env.set('id', String(body.id));",
        variables={},
        request_fields=dict(_REQ),
        response_fields={"status": 200, "headers": {}, "body": '{"id": 99}'},
    )
    assert result.env_mutations == {"id": "99"}


def test_crypto_hmac_sha256() -> None:
    result = run_script(
        "dm.env.set('sig', dm.crypto.hmacSha256('secret', 'payload'));",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    expected = hmac.new(b"secret", b"payload", hashlib.sha256).hexdigest()
    assert result.env_mutations.get("sig") == expected


def test_multiple_console_logs_captured_in_order() -> None:
    result = run_script(
        "dm.console.log('a'); dm.console.log('b'); dm.console.log('c');",
        variables={},
        request_fields=dict(_REQ),
        response_fields=None,
    )
    assert result.logs == ["a", "b", "c"]
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/unit/test_scripting.py -v
```

Expected: `ImportError` — `drummer.core.scripting` does not exist yet.

- [ ] **Step 4: Implement `scripting.py`**

Create `drummer/core/scripting.py`:

```python
import hashlib
import hmac as _hmac
import json
from typing import Any

import quickjs
from pydantic import BaseModel

from drummer.core.debugger import suggest

_DEFAULT_TIMEOUT_MS = 5000

_DM_SETUP_PRE = """
Object.defineProperty(dm, 'response', {
    get: function() {
        throw new Error("dm.response is not available in pre-scripts — move this to a post-script.");
    },
    enumerable: false,
    configurable: false
});
"""

_DM_SETUP_POST = """
dm.response = {
    status: __resp_status,
    headers: __resp_headers,
    text: function() { return __resp_body; },
    json: function() { return JSON.parse(__resp_body); }
};
"""


class ScriptResult(BaseModel):
    logs: list[str] = []
    error: str | None = None
    suggestion: str | None = None
    env_mutations: dict[str, str] = {}
    request_mutations: dict[str, Any] = {}


def run_script(
    script: str,
    *,
    variables: dict[str, str],
    request_fields: dict[str, Any],
    response_fields: dict[str, Any] | None,
    timeout_ms: int = _DEFAULT_TIMEOUT_MS,
) -> ScriptResult:
    logs: list[str] = []
    env_mutations: dict[str, str] = {}
    current_env = dict(variables)

    ctx = quickjs.Context()
    ctx.set_time_limit(timeout_ms / 1000)

    def _console_log(*args: object) -> None:
        logs.append(" ".join(str(a) for a in args))

    def _env_get(key: object) -> str | None:
        return current_env.get(str(key))

    def _env_set(key: object, val: object) -> None:
        k, v = str(key), str(val)
        current_env[k] = v
        env_mutations[k] = v

    def _hmac_sha256(key: object, data: object) -> str:
        return _hmac.new(
            str(key).encode(), str(data).encode(), hashlib.sha256
        ).hexdigest()

    ctx.add_callable("__console_log", _console_log)
    ctx.add_callable("__env_get", _env_get)
    ctx.add_callable("__env_set", _env_set)
    ctx.add_callable("__hmac_sha256", _hmac_sha256)

    ctx.set("__req", ctx.parse_json(json.dumps(request_fields)))

    if response_fields is not None:
        ctx.set("__resp_status", response_fields["status"])
        ctx.set("__resp_body", response_fields["body"])
        ctx.set("__resp_headers", ctx.parse_json(json.dumps(response_fields["headers"])))

    dm_js = """
var dm = {
    env: {
        get: function(key) { return __env_get(key); },
        set: function(key, val) { __env_set(key, String(val)); }
    },
    request: __req,
    crypto: {
        hmacSha256: function(key, data) { return __hmac_sha256(key, data); }
    },
    console: {
        log: function() {
            var args = [];
            for (var i = 0; i < arguments.length; i++) args.push(String(arguments[i]));
            __console_log(args.join(' '));
        }
    }
};
"""
    ctx.eval(dm_js)
    ctx.eval(_DM_SETUP_POST if response_fields is not None else _DM_SETUP_PRE)

    try:
        ctx.eval(script)
    except quickjs.JSException as exc:
        error = str(exc)
        return ScriptResult(logs=logs, error=error, suggestion=suggest(error))

    req_json = ctx.eval("JSON.stringify(__req)")
    request_mutations: dict[str, Any] = json.loads(str(req_json))

    return ScriptResult(
        logs=logs,
        env_mutations=env_mutations,
        request_mutations=request_mutations,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_scripting.py -v
```

Expected: All 12 tests PASS.

- [ ] **Step 6: Run full check**

```bash
make check
```

Expected: All pass (pyright resolves `quickjs` via the new stub).

- [ ] **Step 7: Commit**

```bash
git add typings/quickjs.pyi pyproject.toml drummer/core/scripting.py \
        drummer/core/debugger.py tests/unit/test_scripting.py
git commit -m "feat: add QuickJS scripting core with dm API and crypto helper"
```

---

### Task 4: Engine + variables integration

**Files:**
- Modify: `drummer/core/engine.py`
- Modify: `drummer/core/variables.py`
- Modify: `tests/unit/test_variables.py`
- Modify: `tests/integration/test_send_route.py`

- [ ] **Step 1: Update `ResolvedRequest` and `RequestResult` in `engine.py`**

Replace the two model definitions in `drummer/core/engine.py`:

```python
from typing import Any

class ResolvedRequest(BaseModel):
    name: str
    method: HttpMethod
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    body: str = ""
    encoding: str = "utf-8"
    cookies: CookieConfig = Field(default_factory=CookieConfig)
    warnings: list[str] = Field(default_factory=list)
    pre_script: str = ""
    post_script: str = ""
    script_timeout_ms: int = 5000
    variables: dict[str, str] = Field(default_factory=dict)


class RequestResult(BaseModel):
    status_code: int
    headers: list[tuple[str, str]]
    body: str
    encoding: str
    elapsed_ms: float
    url: str
    warnings: list[str]
    script_logs: list[str] = Field(default_factory=list)
    script_error: str | None = None
    script_suggestion: str | None = None
```

- [ ] **Step 2: Write failing integration tests for scripting in the send pipeline**

Add to `tests/integration/test_send_route.py`:

```python
async def test_pre_script_sets_header(project_dir: Path) -> None:
    (project_dir / "scripted.md").write_text(
        "---\nname: S\nmethod: GET\nurl: https://api.example.com\n"
        "pre_script: \"dm.request.headers['X-Test'] = 'injected';\"\n---\n",
        encoding="utf-8",
    )
    app = _make_app(project_dir)
    await _init_db_for(project_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/send", json={"path": "scripted.md"})
    assert response.status_code == HTTPStatus.OK
    events = parse_sse(response.text)
    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["script_logs"] == []
    assert done["data"]["script_error"] is None


async def test_post_script_env_mutation_captured(project_dir: Path) -> None:
    (project_dir / "scripted.md").write_text(
        "---\nname: S\nmethod: GET\nurl: https://api.example.com\n"
        "post_script: \"dm.console.log('status: ' + dm.response.status);\"\n---\n",
        encoding="utf-8",
    )
    app = _make_app(project_dir, content=b'{"ok":true}')
    await _init_db_for(project_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/send", json={"path": "scripted.md"})
    assert response.status_code == HTTPStatus.OK
    events = parse_sse(response.text)
    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["script_logs"] == ["status: 200"]
    assert done["data"]["script_error"] is None


async def test_failing_pre_script_skips_http_send(project_dir: Path) -> None:
    (project_dir / "scripted.md").write_text(
        "---\nname: S\nmethod: GET\nurl: https://api.example.com\n"
        "pre_script: \"throw new Error('abort');\"\n---\n",
        encoding="utf-8",
    )
    app = _make_app(project_dir)
    await _init_db_for(project_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/send", json={"path": "scripted.md"})
    assert response.status_code == HTTPStatus.OK
    events = parse_sse(response.text)
    event_names = [e["event"] for e in events]
    # No status/headers/body events — HTTP send was skipped
    assert "status" not in event_names
    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["script_error"] is not None


async def test_failing_post_script_still_returns_response(project_dir: Path) -> None:
    (project_dir / "scripted.md").write_text(
        "---\nname: S\nmethod: GET\nurl: https://api.example.com\n"
        "post_script: \"throw new Error('post fail');\"\n---\n",
        encoding="utf-8",
    )
    app = _make_app(project_dir, content=b'{"ok":true}')
    await _init_db_for(project_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/send", json={"path": "scripted.md"})
    assert response.status_code == HTTPStatus.OK
    events = parse_sse(response.text)
    event_names = [e["event"] for e in events]
    # HTTP response events still present
    assert "status" in event_names
    assert "body" in event_names
    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["script_error"] is not None
```

- [ ] **Step 3: Run integration tests to verify they fail**

```bash
pytest tests/integration/test_send_route.py -v -k "script"
```

Expected: All 4 new tests FAIL (scripting not wired into engine yet).

- [ ] **Step 4: Update `variables.py` to copy script fields and variables dict**

Replace the `resolve()` function in `drummer/core/variables.py`:

```python
_SCRIPT_TIMEOUT_DEFAULT = 5000


def resolve(
    request_file: RequestFile,
    env: dict[str, str],
    project_timeout_ms: int | None = None,
) -> ResolvedRequest:
    fm = request_file.frontmatter
    seen: set[str] = set()

    def sub(text: str) -> str:
        result, warns = substitute(text, env)
        seen.update(warns)
        return result

    url = sub(fm.url)
    params = {k: sub(v) for k, v in fm.params.items()}
    headers = {k: sub(v) for k, v in fm.headers.items()}
    body = sub(request_file.body)

    auth = fm.auth
    if auth.type == AuthType.BEARER:
        headers["Authorization"] = f"Bearer {sub(auth.token)}"
    elif auth.type == AuthType.BASIC:
        username = sub(auth.username)
        password = sub(auth.password)
        encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    elif auth.type == AuthType.API_KEY:
        headers[sub(auth.key)] = sub(auth.value)

    effective_timeout = fm.script_timeout_ms or project_timeout_ms or _SCRIPT_TIMEOUT_DEFAULT

    return ResolvedRequest(
        name=fm.name,
        method=fm.method,
        url=url,
        headers=headers,
        params=params,
        body=body,
        encoding=fm.encoding,
        cookies=fm.cookies,
        warnings=sorted(seen),
        pre_script=fm.pre_script,
        post_script=fm.post_script,
        script_timeout_ms=effective_timeout,
        variables=dict(env),
    )
```

Add the required import at the top of `variables.py` (already has `ResolvedRequest` imported from `drummer.core.engine`).

- [ ] **Step 5: Update `engine.py` to wire pre/post scripts**

Replace the full `send()` function in `drummer/core/engine.py`. Add these imports at the top of the file:

```python
from typing import Any
from drummer.core.scripting import run_script
```

Replace the `send()` function:

```python
async def send(
    resolved: ResolvedRequest,
    cookie_jar: CookieJar,
    transport: httpx.AsyncBaseTransport | None = None,
) -> RequestResult:
    all_logs: list[str] = []
    script_error: str | None = None
    script_suggestion: str | None = None
    variables = dict(resolved.variables)

    send_url: str = resolved.url
    send_method: str = resolved.method
    send_headers: dict[str, str] = dict(resolved.headers)
    send_params: dict[str, str] = dict(resolved.params)
    send_body: str = resolved.body

    if resolved.pre_script:
        pre = run_script(
            resolved.pre_script,
            variables=variables,
            request_fields={
                "url": send_url,
                "method": send_method,
                "headers": send_headers,
                "params": send_params,
                "body": send_body,
            },
            response_fields=None,
            timeout_ms=resolved.script_timeout_ms,
        )
        all_logs.extend(pre.logs)
        if pre.error:
            return RequestResult(
                status_code=0,
                headers=[],
                body="",
                encoding="utf-8",
                elapsed_ms=0.0,
                url=resolved.url,
                warnings=resolved.warnings,
                script_logs=all_logs,
                script_error=pre.error,
                script_suggestion=pre.suggestion,
            )
        variables.update(pre.env_mutations)
        mut: dict[str, Any] = pre.request_mutations
        send_url = str(mut.get("url", send_url))
        send_method = str(mut.get("method", send_method))
        send_headers = dict(mut.get("headers", send_headers))
        send_params = dict(mut.get("params", send_params))
        send_body = str(mut.get("body", send_body))

    cookies = cookie_jar.cookies_for_request(
        send_url, resolved.cookies.mode, resolved.cookies.cookies
    )
    content = encode_body(send_body, resolved.encoding) if send_body else None

    async with httpx.AsyncClient(
        transport=transport, cookies=cookies, follow_redirects=False
    ) as client:
        start = time.monotonic()
        response = await client.request(
            method=send_method,
            url=send_url,
            headers=send_headers,
            params=send_params,
            content=content,
        )
        elapsed_ms = (time.monotonic() - start) * 1000

    if resolved.cookies.mode == CookieMode.SESSION:
        set_cookie_headers = [
            v for k, v in response.headers.multi_items() if k.lower() == "set-cookie"
        ]
        if set_cookie_headers:
            cookie_jar.update_from_response(str(response.url), set_cookie_headers)

    encoding = detect_encoding(response.headers.get("content-type", ""), response.content)
    body = decode_body(response.content, encoding)

    if resolved.post_script:
        resp_headers: dict[str, str] = dict(response.headers.items())
        post = run_script(
            resolved.post_script,
            variables=variables,
            request_fields={
                "url": send_url,
                "method": send_method,
                "headers": send_headers,
                "params": send_params,
                "body": send_body,
            },
            response_fields={"status": response.status_code, "headers": resp_headers, "body": body},
            timeout_ms=resolved.script_timeout_ms,
        )
        all_logs.extend(post.logs)
        if post.error:
            script_error = post.error
            script_suggestion = post.suggestion

    return RequestResult(
        status_code=response.status_code,
        headers=list(response.headers.multi_items()),
        body=body,
        encoding=encoding,
        elapsed_ms=elapsed_ms,
        url=str(response.url),
        warnings=resolved.warnings,
        script_logs=all_logs,
        script_error=script_error,
        script_suggestion=script_suggestion,
    )
```

- [ ] **Step 6: Run integration tests to verify they pass**

```bash
pytest tests/integration/test_send_route.py -v -k "script"
```

Expected: All 4 new scripting tests PASS.

- [ ] **Step 7: Run full check**

```bash
make check
```

Expected: All 119+ tests pass, pyright clean.

- [ ] **Step 8: Commit**

```bash
git add drummer/core/engine.py drummer/core/variables.py \
        tests/unit/test_variables.py tests/integration/test_send_route.py
git commit -m "feat: wire pre/post scripts into engine send pipeline"
```

---

### Task 5: SSE send route — script output in `done` event

**Files:**
- Modify: `drummer/api/routes/send.py`

- [ ] **Step 1: Update the send route to load project config and emit script output**

In `drummer/api/routes/send.py`, add the import:

```python
from drummer.core.storage.project import ProjectMeta, load_project
```

Replace the `generate()` inner function inside `send_request_route`. The key changes are:
1. Load project config before resolving, to get `project_timeout_ms`
2. Pass `project_timeout_ms` to `resolve()`
3. Include script output fields in the `done` event

Here is the updated `generate()` function:

```python
    async def generate() -> AsyncGenerator[dict[str, str], None]:
        try:
            req_path = _safe_path(project_dir, body.path)
            request_file = parse_request_file(req_path)
            env_path = project_dir / ".drummer" / "environments" / f"{environment}.yaml"
            env = load_environment(env_path) if env_path.exists() else None
            variables: dict[str, str] = {**(env.variables if env else {}), **body.overrides}

            project_timeout_ms: int | None = None
            try:
                meta = load_project(project_dir)
                project_timeout_ms = meta.script_timeout_ms
            except (OSError, ValueError):
                pass

            resolved = resolve(request_file, variables, project_timeout_ms=project_timeout_ms)
            result = await engine_send(resolved, cookie_jar, transport=transport)

            if result.script_error and result.status_code == 0:
                # Pre-script failed — skip HTTP events, go straight to done
                yield {
                    "event": "done",
                    "data": json.dumps(
                        {
                            "history_id": None,
                            "script_logs": result.script_logs,
                            "script_error": result.script_error,
                            "script_suggestion": result.script_suggestion,
                        }
                    ),
                }
                return

            yield {
                "event": "status",
                "data": json.dumps({"status_code": result.status_code, "url": result.url}),
            }
            yield {"event": "headers", "data": json.dumps(result.headers)}
            yield {
                "event": "body",
                "data": json.dumps(
                    {
                        "body": result.body,
                        "encoding": result.encoding,
                        "elapsed_ms": result.elapsed_ms,
                    }
                ),
            }

            record_id = str(uuid4())
            async with db_factory() as session:
                record = ResponseHistoryRecord(
                    id=record_id,
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
                session.add(record)
                await session.commit()

            yield {
                "event": "done",
                "data": json.dumps(
                    {
                        "history_id": record_id,
                        "script_logs": result.script_logs,
                        "script_error": result.script_error,
                        "script_suggestion": result.script_suggestion,
                    }
                ),
            }

        except (
            OSError,
            ValueError,
            ValidationError,
            httpx.HTTPError,
            httpx.TransportError,
            yaml.YAMLError,
        ) as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}
```

- [ ] **Step 2: Run full check**

```bash
make check
```

Expected: All tests pass. The 4 integration tests added in Task 4 now verify the `done` event payload includes `script_logs` and `script_error`.

- [ ] **Step 3: Commit**

```bash
git add drummer/api/routes/send.py
git commit -m "feat: include script output in SSE done event; load project timeout config"
```

---

### Task 6: Frontend types + stores

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/store/responseStore.ts`
- Modify: `frontend/src/api/useSend.ts`

- [ ] **Step 1: Update `types.ts`**

Add `script_timeout_ms` to `RequestFrontmatter` in `frontend/src/types.ts`:

```typescript
export interface RequestFrontmatter {
  name: string;
  method: HttpMethod;
  url: string;
  headers: Record<string, string>;
  params: Record<string, string>;
  encoding: string;
  cookies: CookieConfig;
  auth: AuthConfig;
  pre_script: string;
  post_script: string;
  script_timeout_ms: number | null;
  tags: string[];
  skip: boolean;
}
```

- [ ] **Step 2: Update `responseStore.ts`**

Add three fields to the interface and initialState in `frontend/src/store/responseStore.ts`:

```typescript
interface ResponseState {
  streaming: StreamingState;
  statusCode: number | null;
  url: string | null;
  responseHeaders: [string, string][];
  body: string | null;
  encoding: string | null;
  elapsedMs: number | null;
  error: string | null;
  historyId: string | null;
  activeTab: ResponseTab;
  scriptLogs: string[];
  scriptError: string | null;
  scriptSuggestion: string | null;

  reset: () => void;
  setStreaming: (state: StreamingState) => void;
  setStatus: (statusCode: number, url: string) => void;
  setHeaders: (headers: [string, string][]) => void;
  setBody: (body: string, encoding: string, elapsedMs: number) => void;
  setDone: (historyId: string | null, scriptLogs: string[], scriptError: string | null, scriptSuggestion: string | null) => void;
  setError: (error: string) => void;
  setTab: (tab: ResponseTab) => void;
}

const initialState = {
  streaming: "idle" as StreamingState,
  statusCode: null,
  url: null,
  responseHeaders: [] as [string, string][],
  body: null,
  encoding: null,
  elapsedMs: null,
  error: null,
  historyId: null,
  activeTab: "body" as ResponseTab,
  scriptLogs: [] as string[],
  scriptError: null,
  scriptSuggestion: null,
};

export const useResponseStore = create<ResponseState>()((set) => ({
  ...initialState,
  reset: () => set({ ...initialState, activeTab: "body" }),
  setStreaming: (streaming) => set({ streaming }),
  setStatus: (statusCode, url) => set({ statusCode, url }),
  setHeaders: (responseHeaders) => set({ responseHeaders }),
  setBody: (body, encoding, elapsedMs) => set({ body, encoding, elapsedMs }),
  setDone: (historyId, scriptLogs, scriptError, scriptSuggestion) =>
    set({ historyId, streaming: "done", scriptLogs, scriptError, scriptSuggestion }),
  setError: (error) => set({ error, streaming: "error" }),
  setTab: (activeTab) => set({ activeTab }),
}));
```

- [ ] **Step 3: Update `useSend.ts` to pass script output to `setDone`**

In `frontend/src/api/useSend.ts`, find the `done` event handler and update the `setDone` call to pass script output fields:

```typescript
case "done": {
  const payload = JSON.parse(data) as {
    history_id: string | null;
    script_logs: string[];
    script_error: string | null;
    script_suggestion: string | null;
  };
  responseStore.setDone(
    payload.history_id,
    payload.script_logs ?? [],
    payload.script_error ?? null,
    payload.script_suggestion ?? null,
  );
  break;
}
```

Also reset script output at the start of a new send (in the same `useSend.ts`, before the SSE connection opens, the store is reset via `responseStore.reset()` — verify this already happens and script fields are cleared by `reset()`).

- [ ] **Step 4: Run frontend type check**

```bash
cd frontend && npm run check
```

Expected: No errors. TypeScript strict mode satisfied.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types.ts frontend/src/store/responseStore.ts frontend/src/api/useSend.ts
git commit -m "feat: add script output fields to responseStore and types"
```

---

### Task 7: ScriptTab UI

**Files:**
- Modify: `frontend/src/components/request/ScriptTab.tsx`
- Modify: `frontend/package.json` (install step)

- [ ] **Step 1: Install `@codemirror/lang-javascript`**

```bash
cd frontend && npm install @codemirror/lang-javascript
```

Verify it appears in `frontend/package.json` under `dependencies`.

- [ ] **Step 2: Implement `ScriptTab.tsx`**

Replace `frontend/src/components/request/ScriptTab.tsx`:

```tsx
import { javascript } from "@codemirror/lang-javascript";
import { EditorState } from "@codemirror/state";
import { oneDark } from "@codemirror/theme-one-dark";
import { EditorView, basicSetup } from "codemirror";
import { useEffect, useRef, useState } from "react";
import { useRequestStore } from "../../store/requestStore";
import { useResponseStore } from "../../store/responseStore";

type ScriptMode = "pre" | "post";

export function ScriptTab() {
  const [mode, setMode] = useState<ScriptMode>("pre");
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  const preScript = useRequestStore(
    (s) => s.draft?.frontmatter.pre_script ?? s.saved?.frontmatter.pre_script ?? "",
  );
  const postScript = useRequestStore(
    (s) => s.draft?.frontmatter.post_script ?? s.saved?.frontmatter.post_script ?? "",
  );
  const patch = useRequestStore((s) => s.patch);

  const scriptLogs = useResponseStore((s) => s.scriptLogs);
  const scriptError = useResponseStore((s) => s.scriptError);
  const scriptSuggestion = useResponseStore((s) => s.scriptSuggestion);

  const patchRef = useRef(patch);
  const modeRef = useRef(mode);
  const initialScriptRef = useRef(preScript);

  useEffect(() => {
    patchRef.current = patch;
  }, [patch]);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  // One-time CodeMirror init
  useEffect(() => {
    if (!editorRef.current) return;
    const view = new EditorView({
      state: EditorState.create({
        doc: initialScriptRef.current,
        extensions: [
          basicSetup,
          javascript(),
          oneDark,
          EditorView.updateListener.of((update) => {
            if (!update.docChanged) return;
            const value = update.state.doc.toString();
            if (modeRef.current === "pre") {
              patchRef.current({ pre_script: value });
            } else {
              patchRef.current({ post_script: value });
            }
          }),
        ],
      }),
      parent: editorRef.current,
    });
    viewRef.current = view;
    return () => view.destroy();
  }, []); // empty dep array: intentional one-time init via refs

  // Sync editor content when mode switches
  const currentScript = mode === "pre" ? preScript : postScript;
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const doc = view.state.doc.toString();
    if (doc !== currentScript) {
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: currentScript },
      });
    }
  }, [mode, currentScript]);

  const hasOutput = scriptLogs.length > 0 || scriptError !== null;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex shrink-0 gap-1 border-b border-gray-700 px-2 pt-1">
        {(["pre", "post"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={`rounded-t px-3 py-1 text-xs ${
              mode === m
                ? "bg-gray-700 text-white"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            {m === "pre" ? "Pre-script" : "Post-script"}
          </button>
        ))}
      </div>

      <div ref={editorRef} className="min-h-0 flex-1 overflow-auto" />

      {hasOutput && (
        <div className="max-h-40 shrink-0 overflow-y-auto border-t border-gray-700 bg-gray-900 p-2 font-mono text-xs">
          {scriptLogs.map((log, i) => (
            <div key={i} className="text-gray-300">
              {log}
            </div>
          ))}
          {scriptError && (
            <div className="mt-1 text-red-400">{scriptError}</div>
          )}
          {scriptSuggestion && (
            <div className="mt-1 text-amber-400">Hint: {scriptSuggestion}</div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Run frontend type and lint check**

```bash
cd frontend && npm run check
```

Expected: No errors.

- [ ] **Step 4: Run full check**

```bash
make check
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json \
        frontend/src/components/request/ScriptTab.tsx
git commit -m "feat: implement ScriptTab with JS editor, sub-tab selector, and output panel"
```

---

### Task 8: ScriptOutput response panel

**Files:**
- Modify: `frontend/src/components/response/ScriptOutput.tsx`

- [ ] **Step 1: Replace the stub**

Replace `frontend/src/components/response/ScriptOutput.tsx`:

```tsx
import { useResponseStore } from "../../store/responseStore";

export function ScriptOutput() {
  const scriptLogs = useResponseStore((s) => s.scriptLogs);
  const scriptError = useResponseStore((s) => s.scriptError);
  const scriptSuggestion = useResponseStore((s) => s.scriptSuggestion);
  const streaming = useResponseStore((s) => s.streaming);

  const hasOutput = scriptLogs.length > 0 || scriptError !== null;

  if (streaming === "idle") {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-gray-400">Send a request to see script output.</p>
      </div>
    );
  }

  if (!hasOutput) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-gray-400">No script output for this request.</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-3 font-mono text-xs">
      {scriptLogs.map((log, i) => (
        <div key={i} className="py-0.5 text-gray-300">
          {log}
        </div>
      ))}
      {scriptError && (
        <div className="mt-2 text-red-400">{scriptError}</div>
      )}
      {scriptSuggestion && (
        <div className="mt-1 text-amber-400">Hint: {scriptSuggestion}</div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Run frontend check**

```bash
cd frontend && npm run check
```

Expected: No errors.

- [ ] **Step 3: Run full check**

```bash
make check
```

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/response/ScriptOutput.tsx
git commit -m "feat: implement ScriptOutput response panel for script logs and errors"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| QuickJS runner + `dm` object | Task 3 |
| `dm.env.get/set` (in-memory) | Task 3 |
| `dm.request.*` (pre, read+write) | Task 3 |
| `dm.response.*` (post, read only) | Task 3 |
| `dm.console.log` captured | Task 3 |
| `dm.crypto.hmacSha256` | Task 3 |
| `dm.response` in pre-script throws | Task 3 |
| Script debugger pattern registry | Task 2 |
| `script_timeout_ms` in `RequestFrontmatter` | Task 1 |
| `script_timeout_ms` in `ProjectMeta` | Task 1 |
| Timeout precedence: request > project > 5000ms | Task 4 (`resolve()`) |
| Pre-script failure skips HTTP send | Task 4 + Task 5 |
| Post-script failure still returns response | Task 4 + Task 5 |
| Script output in SSE `done` event | Task 5 |
| `responseStore` script fields | Task 6 |
| `useSend.ts` parses script output from `done` | Task 6 |
| ScriptTab: sub-tab, editor, output panel | Task 7 |
| ScriptOutput response panel | Task 8 |

All spec requirements covered.

**Parallelism notes:**
- Task 1 is independent — can start immediately.
- Tasks 2 and 3 are independent of each other and of Task 1 — can run in parallel after Task 1.
- Task 4 depends on Tasks 1, 2, and 3.
- Task 5 depends on Task 4.
- Task 6 is independent of Tasks 2–5 — can start after Task 1.
- Tasks 7 and 8 depend on Task 6.
