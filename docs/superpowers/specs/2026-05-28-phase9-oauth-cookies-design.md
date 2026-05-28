# Phase 9 Design: OAuth + Cookies

**Date:** 2026-05-28  
**Status:** Approved

## Overview

Phase 9 adds two capabilities to Drummer:

1. **Persistent cookie store** — the in-memory `CookieJar` is extended with write-through SQLite persistence and expiry tracking (name + value + `expires_at`). Cookies survive restarts and expired cookies are pruned automatically.

2. **OAuth 2.0 Client Credentials** — a new `oauth2_cc` auth type. When a request is sent, the engine fetches a token from the configured `token_url`, caches it in memory until near-expiry, and injects it as `Authorization: Bearer <token>`.

---

## Data Model

### Python (`drummer/core/storage/formats.py`)

`AuthType` gains a new value:

```python
class AuthType(StrEnum):
    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    API_KEY = "api_key"
    OAUTH2_CC = "oauth2_cc"
```

`AuthConfig` gains four new optional fields (default empty — backward compatible with all existing request files):

```python
class AuthConfig(BaseModel):
    type: AuthType = AuthType.NONE
    token: str = ""
    username: str = ""
    password: str = ""
    key: str = ""
    value: str = ""
    # OAuth 2.0 Client Credentials
    token_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    scope: str = ""
```

No changes to `CookieConfig` or `CookieMode` — the existing SESSION/DISABLED/EXPLICIT model is unchanged.

### SQLite (`drummer/api/db/models.py`)

New `CookieRecord` model alongside `ResponseHistoryRecord`:

| Column | Type | Notes |
|---|---|---|
| `hostname` | TEXT | partition key |
| `name` | TEXT | cookie name |
| `value` | TEXT | cookie value |
| `expires_at` | DATETIME nullable | NULL = session cookie (kept until explicitly cleared) |

Primary key: `(hostname, name)`. Writes use upsert semantics.

`init_db` already calls `Base.metadata.create_all` — adding the model is sufficient to create the table.

### TypeScript (`frontend/src/types.ts`)

```typescript
export type AuthType = "none" | "bearer" | "basic" | "api_key" | "oauth2_cc";

export interface AuthConfig {
  type: AuthType;
  token: string;
  username: string;
  password: string;
  key: string;
  value: string;
  token_url: string;
  client_id: string;
  client_secret: string;
  scope: string;
}
```

---

## Backend

### `drummer/core/cookies.py` — extended

`CookieJar` stores `(value, expires_at: datetime | None)` per cookie instead of a bare `str`. Before returning cookies from `cookies_for_request()`, expired entries are pruned. On `update_from_response()`, the `expires`/`max-age` attribute is parsed from the Set-Cookie header and the result is written through to `CookiePersistence`.

`CookiePersistence` is a new async helper class in the same file:
- `load(jar: CookieJar)` — reads all rows from SQLite, prunes already-expired rows, populates the jar.
- `save(hostname, name, value, expires_at)` — upserts the row on every new/updated cookie.
- `clear()` — deletes all rows from the SQLite table.

`CookieJar.__init__` accepts an optional `persistence: CookiePersistence | None = None`. When `None` (tests, in-memory mode) all persistence calls are skipped — existing behavior is fully preserved.

`CookieJar` exposes two async methods that delegate to persistence:
- `load_from_db()` — calls `persistence.load(self)` if persistence is set; no-op otherwise.
- `clear()` is extended to also call `persistence.clear()` when persistence is set, so `DELETE /api/cookies` wipes both the in-memory store and the SQLite table.

### `drummer/core/oauth.py` — new file

**`OAuthToken`** — dataclass: `access_token: str`, `expires_at: datetime | None`.

**`OAuthTokenCache`** — in-memory dict `dict[tuple[str, str], OAuthToken]` keyed by `(token_url, client_id)`.
- `get(token_url, client_id) -> OAuthToken | None` — returns `None` if missing or within 30 s of expiry.
- `set(token_url, client_id, token: OAuthToken)` — stores the token.

**`OAuthError`** — exception subclass of `Exception`. Raised on HTTP errors or malformed token responses.

**`fetch_cc_token(token_url, client_id, client_secret, scope, transport=None) -> OAuthToken`** — async function. POSTs `grant_type=client_credentials` (plus `scope` if non-empty) to `token_url` via httpx. Parses `access_token` and optional `expires_in` from the JSON response. Raises `OAuthError` on non-2xx or missing `access_token`.

**`get_or_fetch_token(cache, auth, transport=None) -> str`** — entry point called by the engine. Checks cache; fetches via `fetch_cc_token` on miss/near-expiry; stores result; returns the access token string.

### `drummer/core/engine.py` — minor extension

`send()` gains an `oauth_cache: OAuthTokenCache` parameter alongside `cookie_jar`.

After pre-script execution, before building the httpx request:

```python
if resolved.auth.type == AuthType.OAUTH2_CC:
    token = await get_or_fetch_token(oauth_cache, resolved.auth, transport)
    send_headers.setdefault("Authorization", f"Bearer {token}")
```

`setdefault` ensures a manually set `Authorization` header takes precedence over the fetched token.

### `drummer/api/app.py` — startup wiring

```python
persistence = CookiePersistence(async_session_factory(db_url))
cookie_jar = CookieJar(persistence=persistence)
# inside lifespan, after init_db:
await cookie_jar.load_from_db()
app.state.cookie_jar = cookie_jar
app.state.oauth_cache = OAuthTokenCache()
```

### `drummer/api/deps.py`

Add `get_oauth_cache(request: Request) -> OAuthTokenCache` alongside the existing `get_cookie_jar`.

### `drummer/api/routes/send.py`

Route handler passes `oauth_cache` (from `app.state` via `get_oauth_cache`) into `send()`. No business logic — thread-through only.

---

## Frontend

### `AuthTab.tsx` — OAuth 2.0 Client Credentials form

The auth type `<select>` gains an `oauth2_cc` option ("OAuth 2.0 Client Credentials"). API Key remains present but disabled. When `oauth2_cc` is selected, four fields appear below the dropdown:

| Field | Label | Input type |
|---|---|---|
| `token_url` | Token URL | text |
| `client_id` | Client ID | text |
| `client_secret` | Client Secret | password |
| `scope` | Scope | text (placeholder "optional") |

All fields patch into `auth` using the existing `update()` pattern.

### `CookiesTab.tsx` — replaces placeholder

Three stacked areas:

**Mode selector** — `<select>` for SESSION / DISABLED / EXPLICIT, patching `cookies.mode`. Always visible.

**Explicit cookie editor** — `<KeyValueTable>` editing `cookies.cookies`. Rendered only when `mode === "explicit"`. Supports add / edit / delete rows, saved to the request frontmatter.

**Session jar viewer** — Read-only section, visible when `mode === "session"`. Calls `GET /api/cookies` and filters client-side to entries matching the current request's hostname (parsed from the URL). Shows a two-column table (Name / Value). Includes a "Clear all" button that calls `DELETE /api/cookies`. Shows "No session cookies for this host" when no matches.

### `frontend/src/api/cookies.ts`

No new API endpoints needed. `GET /api/cookies` already returns `{ [hostname]: { [name]: value } }`. Hostname filtering happens client-side in `CookiesTab`.

---

## Testing

### Unit tests

**`tests/unit/test_oauth.py`**
- Cache miss returns `None`
- Cache hit returns valid token
- Cache returns `None` for token within 30 s of expiry (grace window)
- `fetch_cc_token` sends `grant_type=client_credentials` in POST body
- `fetch_cc_token` includes `scope` when non-empty; omits when empty
- `fetch_cc_token` parses `expires_in` and computes `expires_at`
- `fetch_cc_token` raises `OAuthError` on non-2xx response
- `fetch_cc_token` raises `OAuthError` when `access_token` absent from response
- `get_or_fetch_token` returns cached token without HTTP call on hit
- `get_or_fetch_token` stores fetched token in cache on miss

**`tests/unit/test_cookies_persistence.py`**
- `cookies_for_request` skips cookies where `expires_at` is in the past
- `update_from_response` parses `max-age=0` as immediate expiry (delete semantics)
- `update_from_response` parses `expires=<RFC date>` correctly
- `update_from_response` stores `expires_at=None` for cookies with no expiry attribute
- `CookieJar` with no `CookiePersistence` works correctly (in-memory mode unchanged)

### Integration tests

**`tests/integration/test_oauth_send.py`**

Uses a mock httpx transport intercepting both the token endpoint and the downstream API:
- Sending with `auth.type == "oauth2_cc"` injects `Authorization: Bearer <token>`
- Token is fetched from `token_url` before the main request
- Token is reused on a second send (single token fetch for two sends)
- Manually set `Authorization` header wins over fetched token
- `OAuthError` surfaces as a `400` API error with a descriptive message

**`tests/integration/test_cookies_persistence.py`**

Uses an in-process SQLite DB:
- Cookies received in a response are written to the DB
- A new `CookieJar` loaded from the same DB contains those cookies
- Expired cookies are pruned on load and not returned
- `DELETE /api/cookies` clears the DB table

### Frontend

No new Vitest tests. Cookie persistence and OAuth injection are covered by backend integration tests. `AuthTab` and `CookiesTab` changes are render-only and follow the same pattern as existing tab tests.

---

## Out of Scope for Phase 9

- **OAuth Authorization Code + PKCE** — requires a localhost callback server and browser redirect. Deferred to a future phase.
- **OAuth Device Code flow** — deferred.
- **OAuth Password Grant** — deprecated; deferred.
- **Workspace-level OAuth token panel** — named, shared OAuth credentials across requests. Deferred.
- **Full RFC 6265 cookie support** — path matching, domain scoping, `Secure`/`HttpOnly` flags. Deferred.
- **API key auth UI** — fields exist in the data model; the UI option stays disabled until a later phase.
- **Per-project cookie jars** — cookies remain global (one jar per Drummer instance).
- **Cookie import/export**.
