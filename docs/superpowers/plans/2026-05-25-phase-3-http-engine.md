# Phase 3: HTTP Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the core HTTP send pipeline — variable substitution, cookie jar, charset encoding, and an async engine — so Phase 4's FastAPI layer has a fully testable, framework-free foundation to call.

**Architecture:** Four focused modules in `drummer/core/`: `encoding.py` (pure charset functions), `cookies.py` (in-memory `CookieJar`), `engine.py` (Pydantic models + async `send()`), and `variables.py` (variable substitution + `resolve()`). `variables.py` imports `ResolvedRequest` from `engine.py`; the engine imports from the other three. No circular dependencies. Tests use `pytest-asyncio` (already configured with `asyncio_mode = "auto"`) and an injected httpx transport — no external mocking library required.

**Tech Stack:** Python 3.12, Pydantic v2, `httpx` (async), `chardet`, `pytest-asyncio`.

---

### File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Modify | `drummer/core/storage/formats.py` | Add `cookies: dict[str, str]` field to `CookieConfig` |
| Create | `drummer/core/encoding.py` | `detect_encoding`, `encode_body`, `decode_body` |
| Create | `drummer/core/cookies.py` | `CookieJar` class |
| Create | `drummer/core/engine.py` | `ResolvedRequest`, `RequestResult` models + `async send()` |
| Create | `drummer/core/variables.py` | `substitute`, `resolve` |
| Create | `tests/unit/test_encoding.py` | Unit tests for encoding module |
| Create | `tests/unit/test_cookies.py` | Unit tests for CookieJar |
| Create | `tests/unit/test_engine.py` | Async unit tests for engine |
| Create | `tests/unit/test_variables.py` | Unit tests for variable resolution |

---

### Task 1: `encoding.py` — charset detection and body coding

**Files:**
- Create: `drummer/core/encoding.py`
- Create: `tests/unit/test_encoding.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_encoding.py`:

```python
from drummer.core.encoding import decode_body, detect_encoding, encode_body


def test_detect_encoding_prefers_content_type_charset() -> None:
    result = detect_encoding("text/html; charset=windows-1252", b"doesn't matter")
    assert result == "windows-1252"


def test_detect_encoding_charset_case_insensitive() -> None:
    result = detect_encoding("text/html; Charset=UTF-8", b"")
    assert result == "UTF-8"


def test_detect_encoding_falls_back_when_no_charset() -> None:
    body = b'{"hello": "world"}'
    result = detect_encoding("application/json", body)
    assert isinstance(result, str) and len(result) > 0


def test_detect_encoding_falls_back_to_utf8_for_empty_body() -> None:
    result = detect_encoding("", b"")
    assert result == "utf-8"


def test_encode_body_utf8() -> None:
    assert encode_body("Hello", "utf-8") == b"Hello"


def test_encode_body_latin1() -> None:
    assert encode_body("café", "latin-1") == "café".encode("latin-1")


def test_decode_body_utf8() -> None:
    assert decode_body(b"Hello", "utf-8") == "Hello"


def test_decode_body_replaces_bad_bytes() -> None:
    bad_bytes = b"\xff\xfe"
    result = decode_body(bad_bytes, "utf-8")
    assert "�" in result
```

- [ ] **Step 2: Run to confirm failure**

```bash
/Users/curtis/dev/claude_projects/drummer/venv/bin/python -m pytest tests/unit/test_encoding.py -v
```

Expected: `ModuleNotFoundError: No module named 'drummer.core.encoding'`

- [ ] **Step 3: Implement `encoding.py`**

Create `drummer/core/encoding.py`:

```python
import chardet


def detect_encoding(content_type: str, body_bytes: bytes) -> str:
    for part in content_type.split(";"):
        stripped = part.strip()
        if stripped.lower().startswith("charset="):
            return stripped.split("=", 1)[1].strip()
    if body_bytes:
        detected = chardet.detect(body_bytes)
        encoding = detected.get("encoding")
        if encoding:
            return encoding
    return "utf-8"


def encode_body(body: str, charset: str) -> bytes:
    return body.encode(charset)


def decode_body(body_bytes: bytes, charset: str) -> str:
    return body_bytes.decode(charset, errors="replace")
```

- [ ] **Step 4: Run to confirm all tests pass**

```bash
/Users/curtis/dev/claude_projects/drummer/venv/bin/python -m pytest tests/unit/test_encoding.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add drummer/core/encoding.py tests/unit/test_encoding.py
git commit -m "feat: implement encoding module with charset detection"
```

---

### Task 2: `CookieConfig` update + `cookies.py`

**Files:**
- Modify: `drummer/core/storage/formats.py` (add `cookies` field to `CookieConfig`)
- Create: `drummer/core/cookies.py`
- Create: `tests/unit/test_cookies.py`

- [ ] **Step 1: Add `cookies` field to `CookieConfig` in `formats.py`**

In `drummer/core/storage/formats.py`, update `CookieConfig`:

```python
class CookieConfig(BaseModel):
    mode: CookieMode = CookieMode.SESSION
    cookies: dict[str, str] = Field(default_factory=dict)
```

Also add `"CookieConfig"` already in `__all__` — no change needed there.

- [ ] **Step 2: Verify existing tests still pass**

```bash
/Users/curtis/dev/claude_projects/drummer/venv/bin/python -m pytest tests/unit/test_formats.py -v
```

Expected: All 15 tests PASS (the new field has a default so nothing breaks).

- [ ] **Step 3: Write failing tests for `CookieJar`**

Create `tests/unit/test_cookies.py`:

```python
from drummer.core.cookies import CookieJar
from drummer.core.storage.formats import CookieMode


def test_session_cookies_accumulate_and_are_sent() -> None:
    jar = CookieJar()
    jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


def test_session_cookies_not_sent_cross_domain() -> None:
    jar = CookieJar()
    jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    cookies = jar.cookies_for_request("http://other.com/users", CookieMode.SESSION, {})
    assert cookies == {}


def test_disabled_returns_empty() -> None:
    jar = CookieJar()
    jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.DISABLED, {})
    assert cookies == {}


def test_explicit_returns_only_inline_dict() -> None:
    jar = CookieJar()
    jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    explicit = {"api_key": "xyz"}
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.EXPLICIT, explicit)
    assert cookies == {"api_key": "xyz"}
    assert "session" not in cookies


def test_clear_removes_all_cookies() -> None:
    jar = CookieJar()
    jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    jar.clear()
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.SESSION, {})
    assert cookies == {}


def test_multiple_set_cookie_headers_all_stored() -> None:
    jar = CookieJar()
    jar.update_from_response(
        "http://api.example.com/login",
        ["session=abc123", "user_id=42"],
    )
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123", "user_id": "42"}


def test_later_cookie_overwrites_earlier() -> None:
    jar = CookieJar()
    jar.update_from_response("http://api.example.com/a", ["session=old"])
    jar.update_from_response("http://api.example.com/b", ["session=new"])
    cookies = jar.cookies_for_request("http://api.example.com/c", CookieMode.SESSION, {})
    assert cookies == {"session": "new"}


def test_cookie_with_attributes_strips_to_name_value() -> None:
    jar = CookieJar()
    jar.update_from_response(
        "http://api.example.com/login",
        ["session=abc123; Path=/; HttpOnly; SameSite=Strict"],
    )
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}
```

- [ ] **Step 4: Run to confirm failure**

```bash
/Users/curtis/dev/claude_projects/drummer/venv/bin/python -m pytest tests/unit/test_cookies.py -v
```

Expected: `ModuleNotFoundError: No module named 'drummer.core.cookies'`

- [ ] **Step 5: Implement `cookies.py`**

Create `drummer/core/cookies.py`:

```python
from urllib.parse import urlparse

from drummer.core.storage.formats import CookieMode


class CookieJar:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, str]] = {}  # hostname → {name: value}

    def cookies_for_request(
        self, url: str, mode: CookieMode, explicit: dict[str, str]
    ) -> dict[str, str]:
        if mode == CookieMode.DISABLED:
            return {}
        if mode == CookieMode.EXPLICIT:
            return dict(explicit)
        hostname = urlparse(url).hostname or ""
        return dict(self._store.get(hostname, {}))

    def update_from_response(self, url: str, set_cookie_headers: list[str]) -> None:
        hostname = urlparse(url).hostname or ""
        if hostname not in self._store:
            self._store[hostname] = {}
        for header in set_cookie_headers:
            name_value = header.split(";")[0].strip()
            if "=" in name_value:
                name, _, value = name_value.partition("=")
                self._store[hostname][name.strip()] = value.strip()

    def clear(self) -> None:
        self._store.clear()
```

- [ ] **Step 6: Run to confirm all tests pass**

```bash
/Users/curtis/dev/claude_projects/drummer/venv/bin/python -m pytest tests/unit/test_cookies.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add drummer/core/storage/formats.py drummer/core/cookies.py tests/unit/test_cookies.py
git commit -m "feat: add CookieJar and extend CookieConfig with explicit cookies field"
```

---

### Task 3: `engine.py` — `ResolvedRequest` and `RequestResult` models

**Files:**
- Create: `drummer/core/engine.py`
- Create: `tests/unit/test_engine.py` (models section only)

- [ ] **Step 1: Write failing tests for the models**

Create `tests/unit/test_engine.py`:

```python
import httpx
import pytest
from pydantic import ValidationError

from drummer.core.cookies import CookieJar
from drummer.core.engine import RequestResult, ResolvedRequest, send
from drummer.core.storage.formats import CookieConfig, CookieMode, HttpMethod


def test_resolved_request_requires_name() -> None:
    with pytest.raises(ValidationError):
        ResolvedRequest.model_validate({"method": "GET", "url": "https://example.com"})


def test_resolved_request_invalid_method_raises() -> None:
    with pytest.raises(ValidationError):
        ResolvedRequest.model_validate({
            "name": "test",
            "method": "INVALID",
            "url": "https://example.com",
        })


def test_resolved_request_defaults() -> None:
    rr = ResolvedRequest(name="Test", method="GET", url="https://example.com")
    assert rr.headers == {}
    assert rr.params == {}
    assert rr.body == ""
    assert rr.encoding == "utf-8"
    assert rr.warnings == []


def test_request_result_stores_all_fields() -> None:
    result = RequestResult(
        status_code=200,
        headers={"content-type": "application/json"},
        body='{"ok": true}',
        encoding="utf-8",
        elapsed_ms=42.5,
        url="https://example.com",
        warnings=["missing_var"],
    )
    assert result.status_code == 200
    assert result.elapsed_ms == 42.5
    assert result.warnings == ["missing_var"]
```

- [ ] **Step 2: Run to confirm failure**

```bash
/Users/curtis/dev/claude_projects/drummer/venv/bin/python -m pytest tests/unit/test_engine.py -v
```

Expected: `ModuleNotFoundError: No module named 'drummer.core.engine'`

- [ ] **Step 3: Implement `engine.py` with models only**

Create `drummer/core/engine.py`:

```python
from pydantic import BaseModel, Field

from drummer.core.storage.formats import CookieConfig, HttpMethod


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


class RequestResult(BaseModel):
    status_code: int
    headers: dict[str, str]
    body: str
    encoding: str
    elapsed_ms: float
    url: str
    warnings: list[str]
```

- [ ] **Step 4: Run to confirm model tests pass**

```bash
/Users/curtis/dev/claude_projects/drummer/venv/bin/python -m pytest tests/unit/test_engine.py -v
```

Expected: The 4 model tests PASS. The `send` import will fail — that's expected (Task 5 adds it). Temporarily comment out `from drummer.core.engine import ... send` if the import itself causes a failure before `send` exists.

Note: If ruff complains about the unused `send` import, keep it — it will be used in Task 5's tests and the test file will be committed as a whole unit then.

Actually: split the import across two lines so that removing `send` for now is clean:

```python
from drummer.core.engine import RequestResult, ResolvedRequest
```

Add `send` back to this import line in Task 5 when implementing the send tests.

- [ ] **Step 5: Commit**

```bash
git add drummer/core/engine.py tests/unit/test_engine.py
git commit -m "feat: add ResolvedRequest and RequestResult Pydantic models"
```

---

### Task 4: `variables.py` — substitute and resolve

**Files:**
- Create: `drummer/core/variables.py`
- Create: `tests/unit/test_variables.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_variables.py`:

```python
import base64
from pathlib import Path

from drummer.core.storage.formats import AuthConfig, AuthType, CookieConfig, RequestFile, RequestFrontmatter
from drummer.core.variables import resolve, substitute


def _make_request_file(tmp_path: Path, **kwargs: object) -> RequestFile:
    fm = RequestFrontmatter(name="Test", **kwargs)  # type: ignore[arg-type]
    return RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")


def test_substitute_replaces_known_var() -> None:
    result, warnings = substitute("{{base_url}}/users", {"base_url": "https://api.example.com"})
    assert result == "https://api.example.com/users"
    assert warnings == []


def test_substitute_leaves_unknown_var_as_placeholder() -> None:
    result, warnings = substitute("{{base_url}}/users", {})
    assert result == "{{base_url}}/users"
    assert "base_url" in warnings


def test_substitute_multiple_vars_partial_resolution() -> None:
    result, warnings = substitute("{{proto}}://{{host}}/{{path}}", {"proto": "https", "host": "api.example.com"})
    assert result == "https://api.example.com/{{path}}"
    assert warnings == ["path"]


def test_substitute_empty_string() -> None:
    result, warnings = substitute("", {"x": "y"})
    assert result == ""
    assert warnings == []


def test_resolve_substitutes_url(tmp_path: Path) -> None:
    rf = _make_request_file(tmp_path, url="{{base_url}}/users")
    resolved = resolve(rf, {"base_url": "https://api.example.com"})
    assert resolved.url == "https://api.example.com/users"
    assert resolved.warnings == []


def test_resolve_substitutes_header_values(tmp_path: Path) -> None:
    rf = _make_request_file(
        tmp_path,
        url="https://api.example.com",
        headers={"Authorization": "Bearer {{token}}"},
    )
    resolved = resolve(rf, {"token": "secret"})
    assert resolved.headers["Authorization"] == "Bearer secret"


def test_resolve_substitutes_params(tmp_path: Path) -> None:
    rf = _make_request_file(
        tmp_path,
        url="https://api.example.com",
        params={"tenant": "{{tenant_id}}"},
    )
    resolved = resolve(rf, {"tenant_id": "acme"})
    assert resolved.params["tenant"] == "acme"


def test_resolve_substitutes_body(tmp_path: Path) -> None:
    fm = RequestFrontmatter(name="Test", url="https://api.example.com")
    rf = RequestFile(frontmatter=fm, body='{"name": "{{username}}"}', path=tmp_path / "req.md")
    resolved = resolve(rf, {"username": "alice"})
    assert resolved.body == '{"name": "alice"}'


def test_resolve_bearer_auth_header(tmp_path: Path) -> None:
    rf = _make_request_file(
        tmp_path,
        url="https://api.example.com",
        auth=AuthConfig(type=AuthType.BEARER, token="my-token"),
    )
    resolved = resolve(rf, {})
    assert resolved.headers["Authorization"] == "Bearer my-token"


def test_resolve_bearer_auth_token_substituted(tmp_path: Path) -> None:
    rf = _make_request_file(
        tmp_path,
        url="https://api.example.com",
        auth=AuthConfig(type=AuthType.BEARER, token="{{token}}"),
    )
    resolved = resolve(rf, {"token": "secret123"})
    assert resolved.headers["Authorization"] == "Bearer secret123"


def test_resolve_basic_auth_header(tmp_path: Path) -> None:
    rf = _make_request_file(
        tmp_path,
        url="https://api.example.com",
        auth=AuthConfig(type=AuthType.BASIC, username="user", password="pass"),
    )
    resolved = resolve(rf, {})
    expected = "Basic " + base64.b64encode(b"user:pass").decode()
    assert resolved.headers["Authorization"] == expected


def test_resolve_api_key_auth_header(tmp_path: Path) -> None:
    rf = _make_request_file(
        tmp_path,
        url="https://api.example.com",
        auth=AuthConfig(type=AuthType.API_KEY, key="X-API-Key", value="mykey"),
    )
    resolved = resolve(rf, {})
    assert resolved.headers["X-API-Key"] == "mykey"


def test_resolve_no_auth_adds_no_authorization_header(tmp_path: Path) -> None:
    rf = _make_request_file(tmp_path, url="https://api.example.com")
    resolved = resolve(rf, {})
    assert "Authorization" not in resolved.headers


def test_resolve_collects_warnings_across_fields(tmp_path: Path) -> None:
    rf = _make_request_file(
        tmp_path,
        url="{{base_url}}/users",
        headers={"X-Tenant": "{{tenant}}"},
    )
    resolved = resolve(rf, {})
    assert set(resolved.warnings) == {"base_url", "tenant"}


def test_resolve_deduplicates_warnings(tmp_path: Path) -> None:
    rf = _make_request_file(
        tmp_path,
        url="{{base_url}}/path",
        headers={"X-Base": "{{base_url}}"},
    )
    resolved = resolve(rf, {})
    assert resolved.warnings.count("base_url") == 1
```

- [ ] **Step 2: Run to confirm failure**

```bash
/Users/curtis/dev/claude_projects/drummer/venv/bin/python -m pytest tests/unit/test_variables.py -v
```

Expected: `ModuleNotFoundError: No module named 'drummer.core.variables'`

- [ ] **Step 3: Implement `variables.py`**

Create `drummer/core/variables.py`:

```python
import base64
import re

from drummer.core.engine import ResolvedRequest
from drummer.core.storage.formats import AuthType, RequestFile

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def substitute(text: str, env: dict[str, str]) -> tuple[str, list[str]]:
    warnings: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in env:
            return env[name]
        warnings.append(name)
        return match.group(0)

    return _VAR_RE.sub(_replace, text), warnings


def resolve(request_file: RequestFile, env: dict[str, str]) -> ResolvedRequest:
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
    )
```

- [ ] **Step 4: Run to confirm all tests pass**

```bash
/Users/curtis/dev/claude_projects/drummer/venv/bin/python -m pytest tests/unit/test_variables.py -v
```

Expected: All 14 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add drummer/core/variables.py tests/unit/test_variables.py
git commit -m "feat: implement variable substitution and request resolution"
```

---

### Task 5: `engine.send()` — async HTTP send

**Files:**
- Modify: `drummer/core/engine.py` (add `send()` function and imports)
- Modify: `tests/unit/test_engine.py` (add send tests)

- [ ] **Step 1: Append send tests to `tests/unit/test_engine.py`**

First, update the import line at the top of `tests/unit/test_engine.py` to include `send`:

```python
from drummer.core.engine import RequestResult, ResolvedRequest, send
```

Then append these tests to the file:

```python
class _MockTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        content: bytes = b"",
    ) -> None:
        self._status_code = status_code
        self._headers = headers or {}
        self._content = content

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=self._status_code,
            headers=self._headers,
            content=self._content,
            request=request,
        )


def _make_resolved(
    url: str = "https://api.example.com/users",
    method: HttpMethod = "GET",
    headers: dict[str, str] | None = None,
    body: str = "",
    cookies: CookieConfig | None = None,
    warnings: list[str] | None = None,
) -> ResolvedRequest:
    return ResolvedRequest(
        name="Test",
        method=method,
        url=url,
        headers=headers or {},
        body=body,
        cookies=cookies or CookieConfig(),
        warnings=warnings or [],
    )


async def test_send_returns_status_and_body() -> None:
    transport = _MockTransport(
        status_code=200,
        headers={"content-type": "application/json; charset=utf-8"},
        content=b'{"users": []}',
    )
    result = await send(_make_resolved(), CookieJar(), transport=transport)
    assert result.status_code == 200
    assert result.body == '{"users": []}'
    assert result.encoding == "utf-8"


async def test_send_records_elapsed_ms() -> None:
    transport = _MockTransport(content=b"")
    result = await send(_make_resolved(), CookieJar(), transport=transport)
    assert result.elapsed_ms >= 0


async def test_send_non_200_does_not_raise() -> None:
    transport = _MockTransport(status_code=404, content=b"Not Found")
    result = await send(_make_resolved(), CookieJar(), transport=transport)
    assert result.status_code == 404
    assert "Not Found" in result.body


async def test_send_passes_warnings_through() -> None:
    transport = _MockTransport(content=b"")
    resolved = _make_resolved(warnings=["missing_var"])
    result = await send(resolved, CookieJar(), transport=transport)
    assert result.warnings == ["missing_var"]


async def test_send_session_cookies_accumulated_from_response() -> None:
    transport = _MockTransport(
        headers={"set-cookie": "session=abc123"},
        content=b"",
    )
    jar = CookieJar()
    await send(_make_resolved(), jar, transport=transport)
    stored = jar.cookies_for_request("https://api.example.com/other", CookieMode.SESSION, {})
    assert stored == {"session": "abc123"}


async def test_send_disabled_cookies_not_accumulated() -> None:
    transport = _MockTransport(
        headers={"set-cookie": "session=abc123"},
        content=b"",
    )
    jar = CookieJar()
    resolved = _make_resolved(cookies=CookieConfig(mode=CookieMode.DISABLED))
    await send(resolved, jar, transport=transport)
    stored = jar.cookies_for_request("https://api.example.com/other", CookieMode.SESSION, {})
    assert stored == {}


async def test_send_500_status_captured() -> None:
    transport = _MockTransport(status_code=500, content=b"Internal Server Error")
    result = await send(_make_resolved(), CookieJar(), transport=transport)
    assert result.status_code == 500
```

- [ ] **Step 2: Run to confirm send tests fail**

```bash
/Users/curtis/dev/claude_projects/drummer/venv/bin/python -m pytest tests/unit/test_engine.py -k "send" -v
```

Expected: `ImportError: cannot import name 'send' from 'drummer.core.engine'`

- [ ] **Step 3: Implement `send()` in `engine.py`**

Add imports and `send()` to the bottom of `drummer/core/engine.py`:

```python
import time

import httpx

from drummer.core.cookies import CookieJar
from drummer.core.encoding import decode_body, detect_encoding, encode_body
from drummer.core.storage.formats import CookieMode


async def send(
    resolved: ResolvedRequest,
    cookie_jar: CookieJar,
    transport: httpx.AsyncBaseTransport | None = None,
) -> RequestResult:
    cookies = cookie_jar.cookies_for_request(
        resolved.url, resolved.cookies.mode, resolved.cookies.cookies
    )
    content = encode_body(resolved.body, resolved.encoding) if resolved.body else None

    async with httpx.AsyncClient(transport=transport) as client:
        start = time.monotonic()
        response = await client.request(
            method=resolved.method,
            url=resolved.url,
            headers=resolved.headers,
            params=resolved.params,
            cookies=cookies,
            content=content,
        )
        elapsed_ms = (time.monotonic() - start) * 1000

    if resolved.cookies.mode == CookieMode.SESSION:
        set_cookie_headers = [
            v for k, v in response.headers.multi_items() if k.lower() == "set-cookie"
        ]
        cookie_jar.update_from_response(str(response.url), set_cookie_headers)

    encoding = detect_encoding(
        response.headers.get("content-type", ""), response.content
    )
    body = decode_body(response.content, encoding)

    return RequestResult(
        status_code=response.status_code,
        headers=dict(response.headers),
        body=body,
        encoding=encoding,
        elapsed_ms=elapsed_ms,
        url=str(response.url),
        warnings=resolved.warnings,
    )
```

- [ ] **Step 4: Run all engine tests**

```bash
/Users/curtis/dev/claude_projects/drummer/venv/bin/python -m pytest tests/unit/test_engine.py -v
```

Expected: All 11 tests PASS (4 model tests + 7 send tests).

- [ ] **Step 5: Commit**

```bash
git add drummer/core/engine.py tests/unit/test_engine.py
git commit -m "feat: implement async engine.send with cookie and encoding support"
```

---

### Task 6: Final `make check` and cleanup

**Files:**
- Modify: `TODO.md`

- [ ] **Step 1: Run full check suite**

```bash
make check
```

This runs ruff check, ruff format, pyright, and pytest. All must pass.

- [ ] **Step 2: Fix any lint or type errors at the root cause**

Watch for:
- **`ANN401`** (`Any` in annotation) — use a more specific type
- **`TCH001/TCH002`** (import should be in `TYPE_CHECKING` block) — move it
- **`S105`** (hardcoded secret in test string) — rename the variable key (e.g. `"session"` instead of `"token"`)
- **`PLR2004`** (magic value comparison) — extract to a named variable or use a set/list comparison
- **Pyright `reportUnknownVariableType`** — add explicit annotation to variable
- **`# type: ignore[arg-type]`** in test_variables.py `_make_request_file` helper — if pyright flags the `**kwargs` spread into `RequestFrontmatter`, replace the helper with explicit construction:

  ```python
  def _make_request_file(tmp_path: Path, **kwargs: object) -> RequestFile:
  ```

  If pyright raises `reportArgumentType` on this, remove the helper entirely and build `RequestFrontmatter` inline in each test that needs it.

Never use `# noqa`, `# type: ignore`, or any suppression comment. Fix the root cause.

- [ ] **Step 3: Re-run after any fixes**

```bash
make check
```

Expected: 0 errors, 0 warnings, all tests pass.

- [ ] **Step 4: Commit fixes if any were needed**

```bash
git add -p
git commit -m "fix: resolve lint and type errors in HTTP engine"
```

- [ ] **Step 5: Update `TODO.md`**

Replace the contents of `TODO.md` with:

```markdown
# TODO

Current sprint: **Phase 3 — HTTP Engine** ✅ Complete

Phase 4 plan not yet written.
```

- [ ] **Step 6: Commit TODO update**

```bash
git add TODO.md
git commit -m "chore: mark Phase 3 HTTP engine complete in TODO"
```

---

## Self-Review

**Spec coverage:**
- ✅ `encoding.py` — `detect_encoding` (Content-Type → chardet → utf-8), `encode_body`, `decode_body`
- ✅ `CookieJar` — SESSION/DISABLED/EXPLICIT modes, hostname scoping, multi-header, clear
- ✅ `CookieConfig.cookies` field for EXPLICIT mode
- ✅ `ResolvedRequest` — all fields from spec, `HttpMethod` constraint, defaults for optional fields
- ✅ `RequestResult` — all fields from spec
- ✅ `substitute` — known vars replaced, unknown left as `{{name}}` with warning
- ✅ `resolve` — url, headers, params, body substituted; all four auth types built; warnings deduped
- ✅ `send` — cookies → encode → send → elapsed → update jar (SESSION only) → decode → return
- ✅ Non-200 responses captured, not raised
- ✅ Transport injection for test seam (no external mock library)
- ✅ All tests async-compatible via `asyncio_mode = "auto"`

**Placeholder scan:** No TBDs or incomplete steps.

**Type consistency:**
- `substitute(text: str, env: dict[str, str]) -> tuple[str, list[str]]` — used consistently in `resolve`
- `resolve(request_file: RequestFile, env: dict[str, str]) -> ResolvedRequest` — consistent in tests
- `send(resolved: ResolvedRequest, cookie_jar: CookieJar, transport=None) -> RequestResult` — consistent in tests
- `cookie_jar.cookies_for_request(url, mode, explicit)` — `explicit` is `resolved.cookies.cookies: dict[str, str]` ✅
- `cookie_jar.update_from_response(url, set_cookie_headers)` — `set_cookie_headers: list[str]` ✅
