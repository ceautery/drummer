# Phase 6: Scripting — Design Spec

**Date:** 2026-05-27
**Phase:** 6 — Scripting
**Status:** Approved

---

## Goal

Add pre/post request scripting to Drummer using QuickJS (already a declared dependency). Users
write JavaScript that runs before or after an HTTP send. The `dm` object is the only API surface
exposed to scripts — consistent with the Postman mental model.

---

## Architecture

Option A was chosen: the engine handles script execution directly. `engine.send()` runs the
pre-script, applies mutations to the resolved request, sends HTTP, then runs the post-script.
Script output travels back through `RequestResult` and reaches the UI via the existing `done`
SSE event.

### Send pipeline (updated)

```
load request file → resolve variables → build ResolvedRequest
  → run pre_script (apply env + request mutations)
  → send HTTP
  → run post_script (apply env mutations)
  → collect script logs/errors into RequestResult
  → store response history
  → yield SSE done event (with script output)
```

If a pre-script fails, the HTTP send is skipped and the error is returned immediately. If a
post-script fails, the HTTP response is still returned — the script error is appended alongside it.

---

## New Files

| Path | Purpose |
|------|---------|
| `drummer/core/scripting.py` | QuickJS runner, `dm` object construction, `ScriptResult` |
| `drummer/core/debugger.py` | Pattern-matching error analysis, returns enriched suggestions |
| `tests/unit/test_scripting.py` | Unit tests for the scripting layer |
| `tests/unit/test_debugger.py` | Unit tests for the debugger |

## Modified Files

| Path | Change |
|------|--------|
| `drummer/core/storage/formats.py` | Add `script_timeout_ms: int \| None = None` to `RequestFrontmatter` |
| `drummer/core/storage/project.py` | Add `script_timeout_ms: int \| None = None` to `ProjectConfig` |
| `drummer/core/engine.py` | Add `pre_script`, `post_script`, `script_timeout_ms` to `ResolvedRequest`; add `script_logs`, `script_error`, `script_suggestion` to `RequestResult`; call `run_script` before/after send |
| `drummer/core/variables.py` | Copy script fields through in `resolve()` |
| `drummer/api/routes/send.py` | Include script output in `done` SSE event payload |
| `frontend/src/types.ts` | Add `script_timeout_ms` to `RequestFrontmatter`; add script output fields to response types |
| `frontend/src/store/responseStore.ts` | Add `scriptLogs`, `scriptError`, `scriptSuggestion` fields |
| `frontend/src/store/requestStore.ts` | Ensure `pre_script`, `post_script`, `script_timeout_ms` are included in draft patch |
| `frontend/src/components/request/ScriptTab.tsx` | Replace stub with editor + output panel |

---

## Core Scripting Layer (`scripting.py`)

### `run_script()`

```python
def run_script(
    script: str,
    *,
    variables: dict[str, str],
    request_fields: dict[str, str],  # url, method, headers, params, body
    response_fields: dict | None,    # None in pre-script
    timeout_ms: int = 5000,
) -> ScriptResult
```

A fresh QuickJS context is created per call. The `dm` object is constructed from Python-side
data structures and exposed to JS. All mutations are returned in `ScriptResult` — the script
never directly mutates Python state.

### `ScriptResult`

```python
class ScriptResult(BaseModel):
    logs: list[str]                  # dm.console.log() output
    error: str | None                # exception message, or None
    suggestion: str | None           # debugger hint, or None
    env_mutations: dict[str, str]    # dm.env.set() calls
    request_mutations: dict[str, str]  # dm.request.* assignments (pre-script only)
```

### `dm` API surface

| Method / property | Available in | Notes |
|-------------------|-------------|-------|
| `dm.env.get(key)` | pre + post | Reads from the current variables dict |
| `dm.env.set(key, val)` | pre + post | In-memory only — never writes to disk |
| `dm.request.url` | pre (read+write) | |
| `dm.request.method` | pre (read+write) | |
| `dm.request.headers` | pre (read+write) | Object map of header name → value |
| `dm.request.params` | pre (read+write) | Object map of param name → value |
| `dm.request.body` | pre (read+write) | Raw string |
| `dm.response.status` | post (read) | HTTP status code integer |
| `dm.response.json()` | post (read) | Parsed response body |
| `dm.response.text()` | post (read) | Raw response body as string |
| `dm.response.headers` | post (read) | Object map of header name → value |
| `dm.console.log(...)` | pre + post | Captured; shown in output panel |
| `dm.crypto.hmacSha256(key, data)` | pre + post | Returns hex string; backed by Python `hmac` — QuickJS has no Web Crypto API |

Accessing `dm.response` in a pre-script, or attempting `dm.request` mutations in a post-script,
throws a JS-level error with a clear message.

### Timeout

Default timeout is 5000ms. Overridden by (in precedence order):

1. `script_timeout_ms` in the request frontmatter
2. `script_timeout_ms` in `project.yaml`
3. Hardcoded default of 5000ms

---

## Script Debugger (`debugger.py`)

```python
def suggest(error: str) -> str | None
```

Runs the error message through an ordered list of `(pattern, suggestion)` pairs. Returns the
first match, or `None`. Called automatically by `run_script` — nothing outside `scripting.py`
needs to import `debugger.py`.

### Initial pattern registry

| Pattern | Suggestion |
|---------|-----------|
| `TypeError: undefined is not an object` | "Response may not be JSON — check Content-Type. Try `dm.response.text()` first." |
| `dm.response` in pre-script | "dm.response is not available in pre-scripts — move this to a post-script." |
| `dm.request` mutation in post-script | "dm.request mutations are ignored in post-scripts — move this to a pre-script." |
| Script timeout | "Script timed out after {N}ms. Check for infinite loops or expensive operations." |
| `SyntaxError` | Shows exact line/column from the QuickJS stack trace. |
| Uncaught exception | Full formatted QuickJS stack trace. |

---

## Engine Changes (`engine.py`)

### `ResolvedRequest` additions

```python
pre_script: str = ""
post_script: str = ""
script_timeout_ms: int = 5000
variables: dict[str, str] = {}   # raw variables dict, for dm.env.get()/set()
```

`resolve()` in `variables.py` populates this field alongside the substituted request fields,
so scripts can read and mutate the live variables dict at engine time.

### `RequestResult` additions

```python
script_logs: list[str] = []
script_error: str | None = None
script_suggestion: str | None = None
```

### Updated pipeline

```python
# 1. Run pre-script
if resolved.pre_script:
    pre_result = run_script(
        resolved.pre_script,
        variables=variables,
        request_fields={...},
        response_fields=None,
        timeout_ms=resolved.script_timeout_ms,
    )
    # Apply env mutations back to variables
    variables.update(pre_result.env_mutations)
    # Apply request mutations to resolved fields
    # ... patch url, headers, params, body
    if pre_result.error:
        return RequestResult(script_error=pre_result.error, ...)  # skip HTTP send

# 2. Send HTTP
result = await httpx_send(resolved, ...)

# 3. Run post-script
if resolved.post_script:
    post_result = run_script(
        resolved.post_script,
        variables=variables,
        request_fields={...},
        response_fields={...},
        timeout_ms=resolved.script_timeout_ms,
    )
    variables.update(post_result.env_mutations)
    # Collect logs and errors

# 4. Merge all script output into RequestResult
```

---

## SSE Changes (`send.py`)

The `done` event payload is extended:

```json
{
  "event": "done",
  "data": {
    "history_id": "...",
    "script_logs": ["Token: abc123"],
    "script_error": null,
    "script_suggestion": null
  }
}
```

No new event types. Script output is always available synchronously before `done` is emitted.

---

## Frontend Changes

### `responseStore.ts` additions

```ts
scriptLogs: string[]
scriptError: string | null
scriptSuggestion: string | null
```

Populated when the `done` SSE event arrives. Cleared when a new send starts.

### `ScriptTab.tsx`

Three parts:

1. **Sub-tab selector** — "Pre-script" / "Post-script" toggle. Both tabs always accessible
   (to allow writing a new script); an empty editor means no script is saved.

2. **CodeMirror editor** — JavaScript language mode. Edits flow into `requestStore` draft
   (`pre_script` or `post_script`). Saved via the existing Cmd+S / Save flow — no separate
   save action.

3. **Output panel** — visible after a send that produced script output. Hidden when
   `scriptLogs` is empty and `scriptError` is null. Shows:
   - Console log lines in sequence, monospace
   - Error in red if `scriptError` is non-null
   - Suggestion in amber below the error if `scriptSuggestion` is non-null

### `script-output` response tab

The existing `script-output` tab type in the response panel reads the same `responseStore`
fields, allowing the user to see script output alongside the response body without switching
back to the request panel.

---

## Data Model Changes

### `project.yaml`

```yaml
name: My API Project
version: "1"
default_environment: local
script_timeout_ms: 30000   # optional; overrides the 5000ms default for all scripts
```

### Request frontmatter

```yaml
script_timeout_ms: 60000   # optional; overrides project-level and default
pre_script: |
  // Compute HMAC-SHA256 signature over the request body
  // and add it as a header before sending.
  const sig = computeHmac(dm.env.get("secret"), dm.request.body);
  dm.request.headers["X-Signature"] = sig;
post_script: |
  const body = dm.response.json();
  dm.env.set("auth_token", body.token);
```

---

## Testing

### Unit tests

- `test_scripting.py` — pre/post script execution, env mutations, request mutations, console
  capture, timeout enforcement, error propagation, `dm.response` in pre-script error, `dm.request`
  mutation in post-script error, `dm.crypto.hmacSha256` produces correct hex digest
- `test_debugger.py` — each pattern in the registry matches the expected suggestion

### Integration tests

- `test_send_route.py` additions — send with pre-script that sets a header, send with
  post-script that reads response JSON, send with failing pre-script (HTTP not sent),
  send with failing post-script (response still returned)

### No new e2e tests in Phase 6

The existing smoke tests cover the send flow. Script-specific e2e tests are deferred until
Phase 7 when the mock server provides a stable local target.

---

## Documentation

The scripting reference should include a worked HMAC-SHA256 example as the primary showcase
of `dm.request.*` mutation:

```js
// Pre-script: sign the request body with HMAC-SHA256
const secret = dm.env.get("signing_secret");
const ts = Date.now().toString();
const payload = ts + "." + dm.request.body;
const signature = dm.crypto.hmacSha256(secret, payload);
dm.request.headers["X-Signature"] = signature;
dm.request.headers["X-Timestamp"] = ts;
```

---

## Out of Scope (Phase 6)

- Persistent environment variable writes (dm.env.set stays in-memory)
- Script import / module system
- Async scripts (QuickJS runs synchronously)
- Script sharing across requests
- OAuth flow (Phase 9)
