# Phase 3: HTTP Engine — Design Spec

**Date:** 2026-05-25
**Status:** Approved

---

## Overview

Phase 3 implements the core HTTP send pipeline: variable substitution, cookie management, charset encoding/decoding, and the async engine that ties them together. The result is a fully callable, independently testable HTTP layer with no web-framework dependency. Phase 4 (API + MCP) will call this engine from FastAPI route handlers.

**Deferred to later phases:**
- Raw byte recording / hex dump (Phase 4)
- Global variables (`~/.config/drummer/globals.yaml`) (future phase)
- Pre/post scripts (Phase 6)
- Persistent cookie store in SQLite (Phase 9)

---

## Module Structure

Four new files in `drummer/core/`:

```
drummer/core/
├── variables.py      # resolve(request_file, env) -> ResolvedRequest
├── cookies.py        # CookieJar class
├── encoding.py       # detect_encoding, encode_body, decode_body
└── engine.py         # ResolvedRequest, RequestResult, async send()
tests/unit/
├── test_variables.py
├── test_cookies.py
├── test_encoding.py
└── test_engine.py    # async, httpx transport injected for mocking
```

---

## Data Models

Both models live in `engine.py` — they are the engine's public interface.

```python
class ResolvedRequest(BaseModel):
    name: str
    method: HttpMethod
    url: str                   # {{vars}} substituted
    headers: dict[str, str]    # base headers + auth header merged in
    params: dict[str, str]     # {{vars}} substituted
    body: str                  # {{vars}} substituted
    encoding: str              # from frontmatter
    cookies: CookieConfig
    warnings: list[str]        # names of unresolved {{vars}}

class RequestResult(BaseModel):
    status_code: int
    headers: dict[str, str]
    body: str                  # decoded text
    encoding: str              # charset detected from response
    elapsed_ms: float
    url: str                   # final URL with query params expanded
    warnings: list[str]        # passed through from ResolvedRequest
```

`RequestResult` never raises on HTTP error status (4xx/5xx). Network failures bubble up as exceptions — caught at the API boundary in Phase 4.

---

## Variable Resolution (`variables.py`)

### `substitute(text, env) -> tuple[str, list[str]]`

Replaces `{{name}}` tokens against the env dict. Unknown vars are left as `{{name}}` in the output (not an error) and their names are appended to the warnings list. Pattern: `\{\{(\w+)\}\}`.

### `resolve(request_file, env) -> ResolvedRequest`

Applies `substitute` to: `url`, all header values, all param values, `body`, and auth fields (`token`, `username`, `password`, `key`, `value`). Collects and deduplicates all warnings across fields.

Builds the auth header and merges it into `headers`:

| Auth type | Header added |
|-----------|-------------|
| `bearer`  | `Authorization: Bearer {token}` |
| `basic`   | `Authorization: Basic {base64(username:password)}` |
| `api_key` | `{key}: {value}` |
| `none`    | nothing added |

Auth field values are variable-substituted before the header is built.

---

## Cookie Jar (`cookies.py`)

### `CookieJar` class

```python
class CookieJar:
    def cookies_for_request(
        self, url: str, mode: CookieMode, explicit: dict[str, str]
    ) -> dict[str, str]: ...

    def update_from_response(
        self, url: str, set_cookie_headers: list[str]
    ) -> None: ...

    def clear(self) -> None: ...
```

| Mode | `cookies_for_request` | `update_from_response` |
|------|-----------------------|------------------------|
| `session` | All accumulated cookies matching the domain | Store by domain → name → value |
| `disabled` | `{}` | No-op |
| `explicit` | Only the `explicit` dict | No-op |

Phase 3 cookie matching is hostname-only (`urlparse(url).hostname`): all cookies stored for a hostname are sent to any path on that hostname. No expiry, no path scoping, no Secure flag. Phase 9 slots in persistent storage and full attribute handling without changing this interface.

### `CookieConfig` update

Add `cookies: dict[str, str]` to the existing model in `formats.py` for explicit mode:

```python
class CookieConfig(BaseModel):
    mode: CookieMode = CookieMode.SESSION
    cookies: dict[str, str] = Field(default_factory=dict)  # EXPLICIT mode
```

This is non-breaking — existing request files with no `cookies.cookies` field get `{}` by default.

---

## Encoding (`encoding.py`)

Three pure functions:

```python
def detect_encoding(content_type: str, body_bytes: bytes) -> str:
    # 1. Parse charset from Content-Type header
    # 2. Fall back to chardet.detect(body_bytes) if absent
    # 3. Fall back to "utf-8"

def encode_body(body: str, charset: str) -> bytes:
    # body.encode(charset) — raises on unknown charset name

def decode_body(body_bytes: bytes, charset: str) -> str:
    # body_bytes.decode(charset, errors="replace")
    # errors="replace" keeps a bad encoding from crashing the response viewer
```

---

## Engine (`engine.py`)

### `send(resolved, cookie_jar, transport=None) -> RequestResult`

```python
async def send(
    resolved: ResolvedRequest,
    cookie_jar: CookieJar,
    transport: httpx.AsyncBaseTransport | None = None,
) -> RequestResult:
```

The `transport` parameter is the test seam — production passes `None` (real network), tests inject a fake transport. No external mocking library required.

**Send pipeline:**

1. `cookie_jar.cookies_for_request(url, resolved.cookies.mode, resolved.cookies.cookies)` → cookies dict
2. `encode_body(resolved.body, resolved.encoding)` if body is non-empty → `content` bytes
3. Start timer
4. `httpx.AsyncClient(transport=transport).request(method, url, headers=..., params=..., cookies=..., content=...)` 
5. Stop timer → `elapsed_ms`
6. Extract `Set-Cookie` response headers → `cookie_jar.update_from_response(url, headers)`
7. `detect_encoding(response.headers.get("content-type", ""), response.content)` → `encoding`
8. `decode_body(response.content, encoding)` → `body`
9. Return `RequestResult`

---

## Testing

All tests in `tests/unit/`, `pytest-asyncio` with `asyncio_mode = "auto"` already configured.

**`test_variables.py`** — pure unit, no I/O:
- Known vars substituted, unknown vars left as `{{name}}` with warning
- Auth header built correctly for all four auth types
- Warnings deduplicated across all fields

**`test_cookies.py`** — `CookieJar` unit tests:
- SESSION: cookies accumulate from Set-Cookie and are sent on next same-domain request
- DISABLED: nothing sent, nothing stored even when Set-Cookie arrives
- EXPLICIT: only the inline dict sent, accumulator untouched

**`test_encoding.py`** — pure unit, no I/O:
- `detect_encoding` prefers Content-Type charset over chardet
- `detect_encoding` falls back to chardet when Content-Type has no charset
- `decode_body` with `errors="replace"` handles bad bytes without raising

**`test_engine.py`** — async, httpx transport injected:
- Happy path: 200 response, body decoded, timing recorded, all result fields populated
- Cookies flow: session cookies sent with request, Set-Cookie updates jar
- Warnings from `ResolvedRequest` pass through to `RequestResult`
- Non-200 status (4xx/5xx) captured correctly — engine does not raise
