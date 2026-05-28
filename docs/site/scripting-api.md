# Scripting API

Drummer runs JavaScript pre-request and post-request scripts using QuickJS — a lightweight embedded JS engine. Scripts access the `dm` global object.

## dm.env

Read and write active environment variables.

```javascript
// Read
const token = dm.env.get("token");    // returns string or null

// Write (persists for the session)
dm.env.set("user_id", body.id.toString());
```

## dm.request

Available in **pre-request scripts only**. Changes take effect on the outgoing request.

| Property | Type | Description |
|---|---|---|
| `dm.request.url` | string | Request URL |
| `dm.request.method` | string | HTTP method |
| `dm.request.headers` | object | Request headers (mutable) |
| `dm.request.params` | object | Query parameters (mutable) |
| `dm.request.body` | string | Request body (mutable) |

**Example — add a timestamp header:**

```javascript
dm.request.headers["X-Timestamp"] = Date.now().toString();
```

## dm.response

Available in **post-request scripts only**. Read-only.

| Property/Method | Type | Description |
|---|---|---|
| `dm.response.status` | number | HTTP status code |
| `dm.response.json()` | any | Parsed JSON body (throws if not JSON) |
| `dm.response.text()` | string | Raw response body |
| `dm.response.headers` | object | Response headers |

**Example — extract an ID from the response:**

```javascript
const body = dm.response.json();
dm.env.set("created_id", body.id.toString());
```

## dm.console

```javascript
dm.console.log("debug info", someValue);
```

All `console.log` output is captured and shown in the Script Output panel, even if the script fails or times out.

## Limits

| Constraint | Value |
|---|---|
| Timeout | 5 seconds |
| Network access | Not available |
| Filesystem access | Not available |

## Script debugger

When a script fails, Drummer shows an actionable suggestion alongside the error:

| Situation | Suggestion shown |
|---|---|
| `TypeError: undefined is not an object` | Response may not be JSON — check Content-Type, try `dm.response.text()` first |
| `dm.env.get("X")` returns null | Variable X is not set in the active environment |
| Script timeout | Check for infinite loops |
| Parse error | Exact line/column with code excerpt |
| Uncaught exception | Full QuickJS stack trace, syntax-highlighted |
