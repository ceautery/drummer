# Phase 9: OAuth + Cookies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent cookie storage (SQLite-backed with expiry) and OAuth 2.0 Client Credentials auth to Drummer.

**Architecture:** `CookiePersistenceProtocol` (in core) + concrete `CookiePersistence` (in api/db) keeps layer boundaries intact. `OAuthTokenCache` lives in `drummer/core/oauth.py`; the engine fetches tokens and injects them as Bearer headers. Cookie `update_from_response` becomes async (write-through to SQLite); `aclear()` is the new async clear-all.

**Tech Stack:** Python/FastAPI/SQLAlchemy/aiosqlite (backend), React/TypeScript (frontend). No new dependencies.

---

## File Map

| File | Action |
|---|---|
| `drummer/core/storage/formats.py` | Add `OAUTH2_CC` to `AuthType`; add 4 OAuth fields to `AuthConfig` |
| `drummer/api/db/models.py` | Add `CookieRecord` model |
| `drummer/core/cookies.py` | Full rewrite: expiry, `CookiePersistenceProtocol`, `aclear()`, async `update_from_response` |
| `drummer/api/db/cookie_persistence.py` | New: concrete `CookiePersistence` using SQLAlchemy |
| `drummer/core/oauth.py` | New: `OAuthToken`, `OAuthTokenCache`, `OAuthError`, `fetch_cc_token`, `get_or_fetch_token` |
| `drummer/core/engine.py` | Add `oauth_cache` param; inject Bearer; `await update_from_response` |
| `drummer/api/deps.py` | Add `get_oauth_cache` |
| `drummer/api/routes/send.py` | Pass `oauth_cache`; add `OAuthError` to except |
| `drummer/api/routes/cookies.py` | Use `await cookie_jar.aclear()` |
| `drummer/api/app.py` | Wire `CookiePersistence` + `load_from_db`; add `oauth_cache` to state |
| `frontend/src/types.ts` | Add `oauth2_cc` to `AuthType`; add 4 fields to `AuthConfig` |
| `frontend/src/components/request/AuthTab.tsx` | Add oauth2_cc form |
| `frontend/src/components/request/CookiesTab.tsx` | Replace placeholder |
| `tests/unit/test_formats.py` | Add oauth2_cc round-trip test |
| `tests/unit/test_db_models.py` | Add `CookieRecord` instantiation test |
| `tests/unit/test_cookies.py` | Make all tests `async def`; add `await` to `update_from_response` calls |
| `tests/unit/test_cookies_persistence.py` | New: expiry pruning unit tests |
| `tests/unit/test_oauth.py` | New: `OAuthTokenCache` + `fetch_cc_token` + `get_or_fetch_token` unit tests |
| `tests/integration/test_cookies_persistence.py` | New: DB round-trip integration tests |
| `tests/integration/test_oauth_send.py` | New: end-to-end OAuth send tests |

---

### Task 1: Python data model — AuthType + AuthConfig

**Files:**
- Modify: `drummer/core/storage/formats.py`
- Modify: `tests/unit/test_formats.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_formats.py`:

```python
def test_auth_type_oauth2_cc_string_value() -> None:
    assert AuthType.OAUTH2_CC == "oauth2_cc"


def test_auth_config_oauth2_cc_roundtrip(tmp_path: Path) -> None:
    req_file = tmp_path / "oauth.md"
    fm = RequestFrontmatter(
        name="OAuth Request",
        url="https://api.example.com/data",
        auth=AuthConfig(
            type=AuthType.OAUTH2_CC,
            token_url="https://auth.example.com/token",
            client_id="client1",
            client_secret="secret1",
            scope="read write",
        ),
    )
    original = RequestFile(frontmatter=fm, body="", path=req_file)
    write_request_file(original)
    loaded = parse_request_file(req_file)
    assert loaded.frontmatter.auth.type == AuthType.OAUTH2_CC
    assert loaded.frontmatter.auth.token_url == "https://auth.example.com/token"
    assert loaded.frontmatter.auth.client_id == "client1"
    assert loaded.frontmatter.auth.client_secret == "secret1"
    assert loaded.frontmatter.auth.scope == "read write"


def test_auth_config_oauth2_cc_defaults() -> None:
    cfg = AuthConfig(type=AuthType.OAUTH2_CC)
    assert cfg.token_url == ""
    assert cfg.client_id == ""
    assert cfg.client_secret == ""
    assert cfg.scope == ""
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /Users/curtis/dev/claude_projects/drummer
venv/bin/pytest tests/unit/test_formats.py::test_auth_type_oauth2_cc_string_value -v
```

Expected: `FAILED` — `AttributeError: 'OAUTH2_CC' is not a member of 'AuthType'`

- [ ] **Step 3: Implement**

In `drummer/core/storage/formats.py`, replace the `AuthType` class:

```python
class AuthType(StrEnum):
    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    API_KEY = "api_key"
    OAUTH2_CC = "oauth2_cc"
```

Replace the `AuthConfig` class:

```python
class AuthConfig(BaseModel):
    type: AuthType = AuthType.NONE
    token: str = ""
    username: str = ""
    password: str = ""
    key: str = ""
    value: str = ""
    token_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    scope: str = ""
```

Also add `AuthType` to the `__all__` list (it is already there — no change needed).

- [ ] **Step 4: Run to confirm pass**

```bash
venv/bin/pytest tests/unit/test_formats.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add drummer/core/storage/formats.py tests/unit/test_formats.py
git commit -m "feat: add oauth2_cc auth type and fields to AuthConfig"
```

---

### Task 2: SQLite CookieRecord model

**Files:**
- Modify: `drummer/api/db/models.py`
- Modify: `tests/unit/test_db_models.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_db_models.py`:

```python
def test_cookie_record_instantiation() -> None:
    from datetime import UTC, datetime

    from drummer.api.db.models import CookieRecord

    record = CookieRecord(
        hostname="api.example.com",
        name="session",
        value="abc123",
        expires_at=datetime(2027, 1, 1, tzinfo=UTC),
    )
    assert record.hostname == "api.example.com"
    assert record.name == "session"
    assert record.value == "abc123"
    assert record.expires_at is not None


def test_cookie_record_nullable_expires() -> None:
    from drummer.api.db.models import CookieRecord

    record = CookieRecord(hostname="x.com", name="tok", value="v", expires_at=None)
    assert record.expires_at is None
```

- [ ] **Step 2: Run to confirm failure**

```bash
venv/bin/pytest tests/unit/test_db_models.py::test_cookie_record_instantiation -v
```

Expected: `FAILED` — `ImportError: cannot import name 'CookieRecord'`

- [ ] **Step 3: Implement**

In `drummer/api/db/models.py`, add the following after the `ResponseHistoryRecord` class:

```python
class CookieRecord(Base):
    __tablename__ = "cookies"

    hostname: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Add `datetime` to the existing import at the top of the file:

```python
from datetime import datetime
```

(The file already imports `datetime` — verify and add if missing.)

- [ ] **Step 4: Run to confirm pass**

```bash
venv/bin/pytest tests/unit/test_db_models.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add drummer/api/db/models.py tests/unit/test_db_models.py
git commit -m "feat: add CookieRecord SQLite model for persistent cookie store"
```

---

### Task 3: Cookie core — expiry, CookiePersistenceProtocol, async update

**Files:**
- Rewrite: `drummer/core/cookies.py`
- Modify: `drummer/core/engine.py` (one line: add `await`)
- Modify: `drummer/api/routes/cookies.py` (use `aclear()`)
- Rewrite: `tests/unit/test_cookies.py` (make all tests `async def`)
- Create: `tests/unit/test_cookies_persistence.py`

- [ ] **Step 1: Write the failing unit tests for expiry**

Create `tests/unit/test_cookies_persistence.py`:

```python
from datetime import UTC, datetime, timedelta

from drummer.core.cookies import CookieJar
from drummer.core.storage.formats import CookieMode


async def test_expired_cookie_not_returned() -> None:
    jar = CookieJar()
    past = (datetime.now(UTC) - timedelta(seconds=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    await jar.update_from_response(
        "http://api.example.com/", [f"session=abc123; expires={past}"]
    )
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert "session" not in cookies


async def test_max_age_zero_removes_cookie() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/", ["session=abc123"])
    await jar.update_from_response("http://api.example.com/", ["session=; max-age=0"])
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert "session" not in cookies


async def test_max_age_positive_cookie_returned() -> None:
    jar = CookieJar()
    await jar.update_from_response(
        "http://api.example.com/", ["session=abc123; max-age=3600"]
    )
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_future_expires_cookie_returned() -> None:
    jar = CookieJar()
    future = (datetime.now(UTC) + timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    await jar.update_from_response(
        "http://api.example.com/", [f"session=abc123; expires={future}"]
    )
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_no_expiry_cookie_always_returned() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/", ["session=abc123"])
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_in_memory_jar_without_persistence_works() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/", ["x=1"])
    jar.clear()
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {}


async def test_aclear_removes_all_cookies() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/", ["session=abc123"])
    await jar.aclear()
    cookies = jar.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {}
```

- [ ] **Step 2: Run to confirm failure**

```bash
venv/bin/pytest tests/unit/test_cookies_persistence.py -v
```

Expected: `FAILED` — `TypeError: object CookieJar can't be used in 'await' expression` (update_from_response is currently sync)

- [ ] **Step 3: Rewrite `drummer/core/cookies.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Protocol
from urllib.parse import urlparse

from drummer.core.storage.formats import CookieMode


class CookiePersistenceProtocol(Protocol):
    async def load(self) -> dict[str, dict[str, tuple[str, datetime | None]]]: ...
    async def save(
        self, hostname: str, name: str, value: str, expires_at: datetime | None
    ) -> None: ...
    async def clear(self) -> None: ...


def _parse_set_cookie(header: str) -> tuple[str, str, datetime | None]:
    parts = [p.strip() for p in header.split(";")]
    name_value = parts[0]
    if "=" not in name_value:
        return "", "", None
    name, _, value = name_value.partition("=")
    name = name.strip()
    value = value.strip()
    expires_at: datetime | None = None
    now = datetime.now(UTC)
    for attr in parts[1:]:
        lower = attr.lower()
        if lower.startswith("max-age="):
            try:
                seconds = int(attr[len("max-age="):].strip())
                expires_at = now + timedelta(seconds=seconds)
            except ValueError:
                pass
        elif lower.startswith("expires=") and expires_at is None:
            try:
                parsed = parsedate_to_datetime(attr[len("expires="):].strip())
                expires_at = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except (TypeError, ValueError, IndexError):
                pass
    return name, value, expires_at


class CookieJar:
    def __init__(self, persistence: CookiePersistenceProtocol | None = None) -> None:
        self._store: dict[str, dict[str, tuple[str, datetime | None]]] = {}
        self._persistence = persistence

    def cookies_for_request(
        self, url: str, mode: CookieMode, explicit: dict[str, str]
    ) -> dict[str, str]:
        if mode == CookieMode.DISABLED:
            return {}
        if mode == CookieMode.EXPLICIT:
            return dict(explicit)
        hostname = urlparse(url).hostname or ""
        now = datetime.now(UTC)
        return {
            name: value
            for name, (value, expires_at) in self._store.get(hostname, {}).items()
            if expires_at is None or expires_at > now
        }

    async def update_from_response(self, url: str, set_cookie_headers: list[str]) -> None:
        hostname = urlparse(url).hostname or ""
        if hostname not in self._store:
            self._store[hostname] = {}
        now = datetime.now(UTC)
        for header in set_cookie_headers:
            name, value, expires_at = _parse_set_cookie(header)
            if not name:
                continue
            if expires_at is not None and expires_at <= now:
                self._store[hostname].pop(name, None)
            else:
                self._store[hostname][name] = (value, expires_at)
            if self._persistence is not None:
                await self._persistence.save(hostname, name, value, expires_at)

    async def load_from_db(self) -> None:
        if self._persistence is not None:
            data = await self._persistence.load()
            self._store.update(data)

    def clear(self) -> None:
        self._store.clear()

    async def aclear(self) -> None:
        self._store.clear()
        if self._persistence is not None:
            await self._persistence.clear()

    def all_cookies(self) -> dict[str, dict[str, str]]:
        now = datetime.now(UTC)
        return {
            hostname: {
                name: value
                for name, (value, expires_at) in cookies.items()
                if expires_at is None or expires_at > now
            }
            for hostname, cookies in self._store.items()
        }
```

- [ ] **Step 4: Update `tests/unit/test_cookies.py`** — make all tests `async def` and `await update_from_response`

Replace the entire file with:

```python
from drummer.core.cookies import CookieJar
from drummer.core.storage.formats import CookieMode


async def test_session_cookies_accumulate_and_are_sent() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_session_cookies_not_sent_cross_domain() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    cookies = jar.cookies_for_request("http://other.com/users", CookieMode.SESSION, {})
    assert cookies == {}


async def test_disabled_returns_empty() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.DISABLED, {})
    assert cookies == {}


async def test_explicit_returns_only_inline_dict() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    explicit = {"api_key": "xyz"}
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.EXPLICIT, explicit)
    assert cookies == {"api_key": "xyz"}
    assert "session" not in cookies


async def test_clear_removes_all_cookies() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/login", ["session=abc123"])
    jar.clear()
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.SESSION, {})
    assert cookies == {}


async def test_multiple_set_cookie_headers_all_stored() -> None:
    jar = CookieJar()
    await jar.update_from_response(
        "http://api.example.com/login", ["session=abc123", "user_id=42"]
    )
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123", "user_id": "42"}


async def test_later_cookie_overwrites_earlier() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://api.example.com/a", ["session=old"])
    await jar.update_from_response("http://api.example.com/b", ["session=new"])
    cookies = jar.cookies_for_request("http://api.example.com/c", CookieMode.SESSION, {})
    assert cookies == {"session": "new"}


async def test_cookie_with_attributes_strips_to_name_value() -> None:
    jar = CookieJar()
    await jar.update_from_response(
        "http://api.example.com/login", ["session=abc123; Path=/; HttpOnly; SameSite=Strict"]
    )
    cookies = jar.cookies_for_request("http://api.example.com/users", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_returned_session_dict_is_a_copy() -> None:
    jar = CookieJar()
    await jar.update_from_response("http://x.com/", ["s=1"])
    result = jar.cookies_for_request("http://x.com/", CookieMode.SESSION, {})
    result["injected"] = "evil"
    assert jar.cookies_for_request("http://x.com/", CookieMode.SESSION, {}) == {"s": "1"}
```

- [ ] **Step 5: Update `drummer/core/engine.py`** — add `await` to `update_from_response`

Find the block (around line 122–127):

```python
    if resolved.cookies.mode == CookieMode.SESSION:
        set_cookie_headers = [
            v for k, v in response.headers.multi_items() if k.lower() == "set-cookie"
        ]
        if set_cookie_headers:
            cookie_jar.update_from_response(str(response.url), set_cookie_headers)
```

Replace with:

```python
    if resolved.cookies.mode == CookieMode.SESSION:
        set_cookie_headers = [
            v for k, v in response.headers.multi_items() if k.lower() == "set-cookie"
        ]
        if set_cookie_headers:
            await cookie_jar.update_from_response(str(response.url), set_cookie_headers)
```

- [ ] **Step 6: Update `drummer/api/routes/cookies.py`** — use `aclear()`

Replace the delete route handler:

```python
@router.delete("/cookies")
async def clear_cookies_route(cookie_jar: CookieJarDep) -> dict[str, str]:
    await cookie_jar.aclear()
    return {"status": "cleared"}
```

- [ ] **Step 7: Run all tests to confirm pass**

```bash
venv/bin/pytest tests/unit/test_cookies.py tests/unit/test_cookies_persistence.py tests/integration/test_cookies_routes.py -v
```

Expected: all pass.

- [ ] **Step 8: Run full check**

```bash
make check
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add drummer/core/cookies.py drummer/core/engine.py drummer/api/routes/cookies.py \
        tests/unit/test_cookies.py tests/unit/test_cookies_persistence.py
git commit -m "feat: add cookie expiry tracking and CookiePersistenceProtocol"
```

---

### Task 4: Concrete CookiePersistence + app wiring + integration tests

**Files:**
- Create: `drummer/api/db/cookie_persistence.py`
- Modify: `drummer/api/app.py`
- Create: `tests/integration/test_cookies_persistence.py`

- [ ] **Step 1: Write the failing integration tests**

Create `tests/integration/test_cookies_persistence.py`:

```python
from datetime import UTC, timedelta, datetime
from pathlib import Path

from drummer.api.db.cookie_persistence import CookiePersistence
from drummer.api.db.session import async_session_factory, init_db
from drummer.core.cookies import CookieJar
from drummer.core.storage.formats import CookieMode


def _db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


async def test_cookies_survive_restart(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    await init_db(db_url)
    factory = async_session_factory(db_url)

    jar1 = CookieJar(persistence=CookiePersistence(factory))
    await jar1.update_from_response("http://api.example.com/", ["session=abc123"])

    jar2 = CookieJar(persistence=CookiePersistence(factory))
    await jar2.load_from_db()
    cookies = jar2.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {"session": "abc123"}


async def test_expired_cookies_not_loaded(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    await init_db(db_url)
    factory = async_session_factory(db_url)

    past = (datetime.now(UTC) - timedelta(seconds=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    jar1 = CookieJar(persistence=CookiePersistence(factory))
    await jar1.update_from_response(
        "http://api.example.com/", [f"session=abc123; expires={past}"]
    )

    jar2 = CookieJar(persistence=CookiePersistence(factory))
    await jar2.load_from_db()
    cookies = jar2.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert "session" not in cookies


async def test_aclear_wipes_db(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    await init_db(db_url)
    factory = async_session_factory(db_url)

    jar1 = CookieJar(persistence=CookiePersistence(factory))
    await jar1.update_from_response("http://api.example.com/", ["session=abc123"])
    await jar1.aclear()

    jar2 = CookieJar(persistence=CookiePersistence(factory))
    await jar2.load_from_db()
    cookies = jar2.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {}


async def test_upsert_overwrites_previous_value(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    await init_db(db_url)
    factory = async_session_factory(db_url)

    jar1 = CookieJar(persistence=CookiePersistence(factory))
    await jar1.update_from_response("http://api.example.com/", ["session=old"])
    await jar1.update_from_response("http://api.example.com/", ["session=new"])

    jar2 = CookieJar(persistence=CookiePersistence(factory))
    await jar2.load_from_db()
    cookies = jar2.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert cookies == {"session": "new"}
```

- [ ] **Step 2: Run to confirm failure**

```bash
venv/bin/pytest tests/integration/test_cookies_persistence.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'drummer.api.db.cookie_persistence'`

- [ ] **Step 3: Create `drummer/api/db/cookie_persistence.py`**

```python
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drummer.api.db.models import CookieRecord


class CookiePersistence:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def load(self) -> dict[str, dict[str, tuple[str, datetime | None]]]:
        now = datetime.now(UTC)
        result: dict[str, dict[str, tuple[str, datetime | None]]] = {}
        async with self._factory() as session:
            rows = await session.execute(select(CookieRecord))
            for record in rows.scalars():
                if record.expires_at is not None:
                    exp = (
                        record.expires_at
                        if record.expires_at.tzinfo
                        else record.expires_at.replace(tzinfo=UTC)
                    )
                    if exp <= now:
                        continue
                    expires_at: datetime | None = exp
                else:
                    expires_at = None
                if record.hostname not in result:
                    result[record.hostname] = {}
                result[record.hostname][record.name] = (record.value, expires_at)
        return result

    async def save(
        self, hostname: str, name: str, value: str, expires_at: datetime | None
    ) -> None:
        async with self._factory() as session:
            stmt = (
                sqlite_insert(CookieRecord)
                .values(hostname=hostname, name=name, value=value, expires_at=expires_at)
                .on_conflict_do_update(
                    index_elements=["hostname", "name"],
                    set_={"value": value, "expires_at": expires_at},
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def clear(self) -> None:
        async with self._factory() as session:
            await session.execute(delete(CookieRecord))
            await session.commit()
```

- [ ] **Step 4: Update `drummer/api/app.py`** — wire persistence and load cookies at startup

Replace the `lifespan` function and `create_app` startup code:

```python
from drummer.api.db.cookie_persistence import CookiePersistence
```

Add this import near the top with the other route imports.

Inside `create_app`, replace:

```python
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        await init_db(db_url)
        yield
```

With:

```python
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        await init_db(db_url)
        await _app.state.cookie_jar.load_from_db()
        yield
```

And replace:

```python
    app.state.cookie_jar = CookieJar()
```

With:

```python
    factory = async_session_factory(db_url)
    app.state.cookie_jar = CookieJar(persistence=CookiePersistence(factory))
```

Note: `async_session_factory` is already imported in `app.py` (via `from drummer.api.db.session import async_session_factory, init_db`). Verify and add if missing.

- [ ] **Step 5: Run integration tests to confirm pass**

```bash
venv/bin/pytest tests/integration/test_cookies_persistence.py -v
```

Expected: all pass.

- [ ] **Step 6: Run full check**

```bash
make check
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add drummer/api/db/cookie_persistence.py drummer/api/app.py \
        tests/integration/test_cookies_persistence.py
git commit -m "feat: implement persistent cookie store with SQLite write-through"
```

---

### Task 5: OAuth core module

**Files:**
- Create: `drummer/core/oauth.py`
- Create: `tests/unit/test_oauth.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_oauth.py`:

```python
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from drummer.core.oauth import OAuthError, OAuthToken, OAuthTokenCache, fetch_cc_token, get_or_fetch_token
from drummer.core.storage.formats import AuthConfig, AuthType

_TOKEN_URL = "https://auth.example.com/token"
_CLIENT_ID = "client1"
_CLIENT_SECRET = "secret1"
_ACCESS_TOKEN = "test-token-abc"


def _ok_transport(body: dict) -> httpx.AsyncBaseTransport:
    content = json.dumps(body).encode()

    class _T(httpx.AsyncBaseTransport):
        async def handle_async_request(self, req: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=content, request=req)

    return _T()


def _error_transport(status: int = 401) -> httpx.AsyncBaseTransport:
    class _T(httpx.AsyncBaseTransport):
        async def handle_async_request(self, req: httpx.Request) -> httpx.Response:
            return httpx.Response(status, content=b'{"error":"unauthorized"}', request=req)

    return _T()


async def test_cache_miss_returns_none() -> None:
    cache = OAuthTokenCache()
    assert cache.get(_TOKEN_URL, _CLIENT_ID) is None


async def test_cache_hit_returns_token() -> None:
    cache = OAuthTokenCache()
    token = OAuthToken(
        access_token=_ACCESS_TOKEN,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    cache.set(_TOKEN_URL, _CLIENT_ID, token)
    result = cache.get(_TOKEN_URL, _CLIENT_ID)
    assert result is not None
    assert result.access_token == _ACCESS_TOKEN


async def test_cache_returns_none_within_grace_window() -> None:
    cache = OAuthTokenCache()
    token = OAuthToken(
        access_token=_ACCESS_TOKEN,
        expires_at=datetime.now(UTC) + timedelta(seconds=20),
    )
    cache.set(_TOKEN_URL, _CLIENT_ID, token)
    assert cache.get(_TOKEN_URL, _CLIENT_ID) is None


async def test_cache_returns_token_with_no_expiry() -> None:
    cache = OAuthTokenCache()
    token = OAuthToken(access_token=_ACCESS_TOKEN, expires_at=None)
    cache.set(_TOKEN_URL, _CLIENT_ID, token)
    result = cache.get(_TOKEN_URL, _CLIENT_ID)
    assert result is not None


async def test_fetch_cc_token_returns_access_token() -> None:
    token = await fetch_cc_token(
        _TOKEN_URL, _CLIENT_ID, _CLIENT_SECRET, "",
        transport=_ok_transport({"access_token": _ACCESS_TOKEN}),
    )
    assert token.access_token == _ACCESS_TOKEN


async def test_fetch_cc_token_includes_scope_when_set() -> None:
    captured: list[httpx.Request] = []

    class _Cap(httpx.AsyncBaseTransport):
        async def handle_async_request(self, req: httpx.Request) -> httpx.Response:
            captured.append(req)
            body = json.dumps({"access_token": _ACCESS_TOKEN}).encode()
            return httpx.Response(200, content=body, request=req)

    await fetch_cc_token(_TOKEN_URL, _CLIENT_ID, _CLIENT_SECRET, "read write", transport=_Cap())
    assert len(captured) == 1
    body_text = captured[0].content.decode()
    assert "scope" in body_text
    assert "read" in body_text


async def test_fetch_cc_token_omits_scope_when_empty() -> None:
    captured: list[httpx.Request] = []

    class _Cap(httpx.AsyncBaseTransport):
        async def handle_async_request(self, req: httpx.Request) -> httpx.Response:
            captured.append(req)
            body = json.dumps({"access_token": _ACCESS_TOKEN}).encode()
            return httpx.Response(200, content=body, request=req)

    await fetch_cc_token(_TOKEN_URL, _CLIENT_ID, _CLIENT_SECRET, "", transport=_Cap())
    body_text = captured[0].content.decode()
    assert "scope" not in body_text


async def test_fetch_cc_token_parses_expires_in() -> None:
    token = await fetch_cc_token(
        _TOKEN_URL, _CLIENT_ID, _CLIENT_SECRET, "",
        transport=_ok_transport({"access_token": _ACCESS_TOKEN, "expires_in": 3600}),
    )
    assert token.expires_at is not None
    assert token.expires_at > datetime.now(UTC) + timedelta(seconds=3590)


async def test_fetch_cc_token_no_expires_in_gives_none() -> None:
    token = await fetch_cc_token(
        _TOKEN_URL, _CLIENT_ID, _CLIENT_SECRET, "",
        transport=_ok_transport({"access_token": _ACCESS_TOKEN}),
    )
    assert token.expires_at is None


async def test_fetch_cc_token_raises_on_http_error() -> None:
    with pytest.raises(OAuthError):
        await fetch_cc_token(
            _TOKEN_URL, _CLIENT_ID, _CLIENT_SECRET, "",
            transport=_error_transport(401),
        )


async def test_fetch_cc_token_raises_on_missing_access_token() -> None:
    with pytest.raises(OAuthError):
        await fetch_cc_token(
            _TOKEN_URL, _CLIENT_ID, _CLIENT_SECRET, "",
            transport=_ok_transport({"token_type": "Bearer"}),
        )


async def test_get_or_fetch_uses_cache_on_hit() -> None:
    cache = OAuthTokenCache()
    token = OAuthToken(
        access_token=_ACCESS_TOKEN,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    cache.set(_TOKEN_URL, _CLIENT_ID, token)
    auth = AuthConfig(
        type=AuthType.OAUTH2_CC,
        token_url=_TOKEN_URL,
        client_id=_CLIENT_ID,
        client_secret=_CLIENT_SECRET,
    )

    class _NeverCalled(httpx.AsyncBaseTransport):
        async def handle_async_request(self, req: httpx.Request) -> httpx.Response:
            raise AssertionError("should not call token endpoint")

    result = await get_or_fetch_token(cache, auth, transport=_NeverCalled())
    assert result == _ACCESS_TOKEN


async def test_get_or_fetch_stores_token_on_miss() -> None:
    cache = OAuthTokenCache()
    auth = AuthConfig(
        type=AuthType.OAUTH2_CC,
        token_url=_TOKEN_URL,
        client_id=_CLIENT_ID,
        client_secret=_CLIENT_SECRET,
    )
    result = await get_or_fetch_token(
        cache, auth,
        transport=_ok_transport({"access_token": _ACCESS_TOKEN, "expires_in": 3600}),
    )
    assert result == _ACCESS_TOKEN
    cached = cache.get(_TOKEN_URL, _CLIENT_ID)
    assert cached is not None
    assert cached.access_token == _ACCESS_TOKEN
```

- [ ] **Step 2: Run to confirm failure**

```bash
venv/bin/pytest tests/unit/test_oauth.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'drummer.core.oauth'`

- [ ] **Step 3: Create `drummer/core/oauth.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from drummer.core.storage.formats import AuthConfig

_GRANT_TYPE = "client_credentials"
_GRACE_SECONDS = 30


class OAuthError(Exception):
    pass


@dataclass
class OAuthToken:
    access_token: str
    expires_at: datetime | None


class OAuthTokenCache:
    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], OAuthToken] = {}

    def get(self, token_url: str, client_id: str) -> OAuthToken | None:
        token = self._cache.get((token_url, client_id))
        if token is None:
            return None
        if token.expires_at is not None:
            if datetime.now(UTC) >= token.expires_at - timedelta(seconds=_GRACE_SECONDS):
                return None
        return token

    def set(self, token_url: str, client_id: str, token: OAuthToken) -> None:
        self._cache[(token_url, client_id)] = token


async def fetch_cc_token(
    token_url: str,
    client_id: str,
    client_secret: str,
    scope: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> OAuthToken:
    data: dict[str, str] = {
        "grant_type": _GRANT_TYPE,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if scope:
        data["scope"] = scope

    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.post(token_url, data=data)

    if response.status_code >= 400:
        msg = f"Token endpoint returned {response.status_code}: {response.text}"
        raise OAuthError(msg)

    try:
        payload: dict[str, object] = response.json()
    except ValueError as exc:
        msg = f"Token response is not valid JSON: {exc}"
        raise OAuthError(msg) from exc

    if "access_token" not in payload:
        msg = "Token response missing 'access_token'"
        raise OAuthError(msg)

    expires_at: datetime | None = None
    raw_expires = payload.get("expires_in")
    if raw_expires is not None:
        try:
            expires_at = datetime.now(UTC) + timedelta(seconds=int(str(raw_expires)))
        except (ValueError, TypeError):
            pass

    return OAuthToken(access_token=str(payload["access_token"]), expires_at=expires_at)


async def get_or_fetch_token(
    cache: OAuthTokenCache,
    auth: AuthConfig,
    transport: httpx.AsyncBaseTransport | None = None,
) -> str:
    cached = cache.get(auth.token_url, auth.client_id)
    if cached is not None:
        return cached.access_token

    token = await fetch_cc_token(
        auth.token_url, auth.client_id, auth.client_secret, auth.scope,
        transport=transport,
    )
    cache.set(auth.token_url, auth.client_id, token)
    return token.access_token
```

- [ ] **Step 4: Run to confirm pass**

```bash
venv/bin/pytest tests/unit/test_oauth.py -v
```

Expected: all pass.

- [ ] **Step 5: Run full check**

```bash
make check
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add drummer/core/oauth.py tests/unit/test_oauth.py
git commit -m "feat: add OAuth 2.0 client credentials core module"
```

---

### Task 6: Engine + route OAuth wiring + integration tests

**Files:**
- Modify: `drummer/core/engine.py`
- Modify: `drummer/api/deps.py`
- Modify: `drummer/api/routes/send.py`
- Modify: `drummer/api/app.py`
- Create: `tests/integration/test_oauth_send.py`

- [ ] **Step 1: Write the failing integration tests**

Create `tests/integration/test_oauth_send.py`:

```python
import json
from pathlib import Path

import httpx
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.api.db.session import init_db
from tests.integration.conftest import parse_sse

_TOKEN_URL = "https://auth.example.com/token"
_API_URL = "https://api.example.com/data"
_ACCESS_TOKEN = "test-token-abc"

_OAUTH_MD = f"""\
---
name: OAuth Test
method: GET
url: {_API_URL}
auth:
  type: oauth2_cc
  token_url: {_TOKEN_URL}
  client_id: client1
  client_secret: secret1
---
"""

_TOKEN_BODY = json.dumps({"access_token": _ACCESS_TOKEN, "expires_in": 3600}).encode()
_API_BODY = json.dumps({"ok": True}).encode()


class _RoutingTransport(httpx.AsyncBaseTransport):
    def __init__(self, routes: dict[str, tuple[int, bytes]]) -> None:
        self._routes = routes
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)
        for prefix, (status, content) in self._routes.items():
            if url.startswith(prefix):
                return httpx.Response(
                    status,
                    headers=[("content-type", "application/json")],
                    content=content,
                    request=request,
                )
        return httpx.Response(404, content=b"not found", request=request)


def _make_app(project_dir: Path, transport: httpx.AsyncBaseTransport) -> object:
    db_url = f"sqlite+aiosqlite:///{project_dir / 'test.db'}"
    app = create_app(project_dir=project_dir, db_url=db_url)
    app.state.transport = transport
    return app


async def test_oauth_cc_injects_bearer_token(project_dir: Path) -> None:
    (project_dir / "oauth.md").write_text(_OAUTH_MD, encoding="utf-8")
    transport = _RoutingTransport({_TOKEN_URL: (200, _TOKEN_BODY), _API_URL: (200, _API_BODY)})
    app = _make_app(project_dir, transport)
    await init_db(f"sqlite+aiosqlite:///{project_dir / 'test.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/send", json={"path": "oauth.md"})
    assert response.status_code == 200
    api_reqs = [r for r in transport.requests if str(r.url).startswith(_API_URL)]
    assert len(api_reqs) == 1
    assert api_reqs[0].headers.get("authorization") == f"Bearer {_ACCESS_TOKEN}"


async def test_oauth_cc_token_reused_on_second_send(project_dir: Path) -> None:
    (project_dir / "oauth.md").write_text(_OAUTH_MD, encoding="utf-8")
    transport = _RoutingTransport({_TOKEN_URL: (200, _TOKEN_BODY), _API_URL: (200, _API_BODY)})
    app = _make_app(project_dir, transport)
    await init_db(f"sqlite+aiosqlite:///{project_dir / 'test.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/send", json={"path": "oauth.md"})
        await ac.post("/api/send", json={"path": "oauth.md"})
    token_reqs = [r for r in transport.requests if str(r.url).startswith(_TOKEN_URL)]
    assert len(token_reqs) == 1


async def test_oauth_cc_manual_auth_header_wins(project_dir: Path) -> None:
    manual_token = "manual-token-xyz"
    md = f"""\
---
name: Manual
method: GET
url: {_API_URL}
headers:
  Authorization: Bearer {manual_token}
auth:
  type: oauth2_cc
  token_url: {_TOKEN_URL}
  client_id: client1
  client_secret: secret1
---
"""
    (project_dir / "manual.md").write_text(md, encoding="utf-8")
    transport = _RoutingTransport({_TOKEN_URL: (200, _TOKEN_BODY), _API_URL: (200, _API_BODY)})
    app = _make_app(project_dir, transport)
    await init_db(f"sqlite+aiosqlite:///{project_dir / 'test.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/send", json={"path": "manual.md"})
    api_reqs = [r for r in transport.requests if str(r.url).startswith(_API_URL)]
    assert api_reqs[0].headers.get("authorization") == f"Bearer {manual_token}"


async def test_oauth_cc_error_surfaces_in_sse(project_dir: Path) -> None:
    (project_dir / "oauth.md").write_text(_OAUTH_MD, encoding="utf-8")
    transport = _RoutingTransport({_TOKEN_URL: (401, b'{"error":"unauthorized"}')})
    app = _make_app(project_dir, transport)
    await init_db(f"sqlite+aiosqlite:///{project_dir / 'test.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/send", json={"path": "oauth.md"})
    events = parse_sse(response.text)
    assert any(e["event"] == "error" for e in events)
    assert not any(e["event"] == "done" for e in events)
```

- [ ] **Step 2: Run to confirm failure**

```bash
venv/bin/pytest tests/integration/test_oauth_send.py::test_oauth_cc_injects_bearer_token -v
```

Expected: `FAILED` — no `Authorization` header injected (engine doesn't know about OAuth yet)

- [ ] **Step 3: Update `drummer/core/engine.py`**

Add imports near the top (with other drummer imports):

```python
from drummer.core.oauth import OAuthTokenCache, get_or_fetch_token
from drummer.core.storage.formats import AuthType, CookieConfig, CookieMode, GraphQLConfig, HttpMethod
```

(Add `AuthType` and `OAuthTokenCache`/`get_or_fetch_token` to the existing imports.)

Change the `send` signature:

```python
async def send(
    resolved: ResolvedRequest,
    cookie_jar: CookieJar,
    *,
    oauth_cache: OAuthTokenCache | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> RequestResult:
```

After the pre-script block (after `send_body` mutations, before `cookies = cookie_jar.cookies_for_request(...)`), add:

```python
    if resolved.auth.type == AuthType.OAUTH2_CC and oauth_cache is not None:
        token = await get_or_fetch_token(oauth_cache, resolved.auth, transport)
        send_headers.setdefault("Authorization", f"Bearer {token}")
```

`ResolvedRequest` currently does NOT have an `auth` field. Add it now.

In `drummer/core/engine.py`, also add `AuthConfig` to the formats import:

```python
from drummer.core.storage.formats import AuthConfig, AuthType, CookieConfig, CookieMode, GraphQLConfig, HttpMethod
```

Add `auth` to `ResolvedRequest` (after the `cookies` field):

```python
class ResolvedRequest(BaseModel):
    name: str
    method: HttpMethod
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    body: str = ""
    encoding: str = "utf-8"
    cookies: CookieConfig = Field(default_factory=CookieConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    warnings: list[str] = Field(default_factory=list)
    pre_script: str = ""
    post_script: str = ""
    script_timeout_ms: int = 5000
    variables: dict[str, str] = Field(default_factory=dict)
    graphql: GraphQLConfig | None = None
```

- [ ] **Step 4: Update `drummer/core/variables.py`** — pass `auth` through to `ResolvedRequest`

`resolve()` currently handles auth by injecting headers for bearer/basic/api_key. For `oauth2_cc` the engine handles it, so `resolve()` just needs to pass `auth` through unchanged.

In `drummer/core/variables.py`, add `auth=fm.auth` to the `ResolvedRequest(...)` constructor call:

```python
    return ResolvedRequest(
        name=fm.name,
        method=fm.method,
        url=url,
        headers=headers,
        params=params,
        body=body,
        encoding=fm.encoding,
        cookies=fm.cookies,
        auth=fm.auth,
        warnings=sorted(seen),
        pre_script=fm.pre_script,
        post_script=fm.post_script,
        script_timeout_ms=effective_timeout,
        variables=dict(env),
        graphql=graphql_resolved,
    )
```

- [ ] **Step 5: Update `drummer/api/deps.py`** — add `get_oauth_cache`

Append to `drummer/api/deps.py`:

```python
from drummer.core.oauth import OAuthTokenCache


def get_oauth_cache(request: Request) -> OAuthTokenCache:
    return cast("OAuthTokenCache", request.app.state.oauth_cache)
```

- [ ] **Step 6: Update `drummer/api/routes/send.py`** — pass `oauth_cache`, handle `OAuthError`

Add imports:

```python
from drummer.api.deps import get_cookie_jar, get_oauth_cache, get_project_dir
from drummer.core.oauth import OAuthError, OAuthTokenCache
```

Add the dependency type:

```python
OAuthCacheDep = Annotated[OAuthTokenCache, Depends(get_oauth_cache)]
```

Update the route signature to accept `oauth_cache`:

```python
@router.post("/send")
async def send_request_route(
    body: SendRequest,
    request: Request,
    project_dir: ProjectDir,
    cookie_jar: CookieJarDep,
    oauth_cache: OAuthCacheDep,
) -> EventSourceResponse:
```

In the `generate()` closure, update the `engine_send` call:

```python
            result = await engine_send(resolved, cookie_jar, oauth_cache=oauth_cache, transport=transport)
```

Add `OAuthError` to the except tuple:

```python
        except (
            OSError,
            ValueError,
            ValidationError,
            httpx.HTTPError,
            httpx.TransportError,
            yaml.YAMLError,
            OAuthError,
        ) as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}
```

- [ ] **Step 7: Update `drummer/api/app.py`** — add `oauth_cache` to app state

Add import:

```python
from drummer.core.oauth import OAuthTokenCache
```

Inside `create_app`, add after the cookie_jar line:

```python
    app.state.oauth_cache = OAuthTokenCache()
```

- [ ] **Step 8: Run integration tests to confirm pass**

```bash
venv/bin/pytest tests/integration/test_oauth_send.py -v
```

Expected: all pass.

- [ ] **Step 9: Run full check**

```bash
make check
```

Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add drummer/core/engine.py drummer/core/variables.py drummer/api/deps.py \
        drummer/api/routes/send.py drummer/api/app.py \
        tests/integration/test_oauth_send.py
git commit -m "feat: wire OAuth client credentials into send engine and API"
```

---

### Task 7: Frontend data model

**Files:**
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Update `frontend/src/types.ts`**

Change `AuthType`:

```typescript
export type AuthType = "none" | "bearer" | "basic" | "api_key" | "oauth2_cc";
```

Change `AuthConfig`:

```typescript
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

- [ ] **Step 2: Run type check**

```bash
make check
```

Expected: TypeScript errors in `AuthTab.tsx` because the default fallback object is missing the new fields. Note the errors — they'll be fixed in Task 8.

If the only errors are in `AuthTab.tsx`, proceed. If there are errors in other files, fix them now.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts
git commit -m "feat: add oauth2_cc to frontend AuthType and AuthConfig"
```

(If `make check` fails due to AuthTab, fix AuthTab in this commit too — see Task 8 Step 2.)

---

### Task 8: Frontend AuthTab — oauth2_cc form

**Files:**
- Modify: `frontend/src/components/request/AuthTab.tsx`

- [ ] **Step 1: Update `AuthTab.tsx`**

Replace the entire file with:

```tsx
import { useRequestStore } from "../../store/requestStore";
import type { AuthType } from "../../types";

export function AuthTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const auth = current?.frontmatter.auth ?? {
    type: "none" as AuthType,
    token: "",
    username: "",
    password: "",
    key: "",
    value: "",
    token_url: "",
    client_id: "",
    client_secret: "",
    scope: "",
  };

  const update = (changes: Partial<typeof auth>) =>
    patch({ auth: { ...auth, ...changes } });

  return (
    <div className="p-3 flex flex-col gap-3">
      <div>
        <label htmlFor="auth-type" className="text-xs text-gray-500">
          Auth type
        </label>
        <select
          id="auth-type"
          className="mt-1 w-48 rounded border px-2 py-1 text-sm"
          value={auth.type}
          onChange={(e) => update({ type: e.target.value as AuthType })}
        >
          <option value="none">None</option>
          <option value="bearer">Bearer Token</option>
          <option value="basic">Basic Auth</option>
          <option value="oauth2_cc">OAuth 2.0 Client Credentials</option>
          <option value="api_key" disabled>
            API Key
          </option>
        </select>
      </div>

      {auth.type === "bearer" && (
        <div>
          <label htmlFor="bearer-token" className="text-xs text-gray-500">
            Token
          </label>
          <input
            id="bearer-token"
            type="text"
            className="mt-1 w-full rounded border px-2 py-1 text-sm font-mono"
            value={auth.token}
            placeholder="Bearer token"
            onChange={(e) => update({ token: e.target.value })}
          />
        </div>
      )}

      {auth.type === "basic" && (
        <>
          <div>
            <label htmlFor="basic-username" className="text-xs text-gray-500">
              Username
            </label>
            <input
              id="basic-username"
              type="text"
              className="mt-1 w-full rounded border px-2 py-1 text-sm"
              value={auth.username}
              onChange={(e) => update({ username: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="basic-password" className="text-xs text-gray-500">
              Password
            </label>
            <input
              id="basic-password"
              type="password"
              className="mt-1 w-full rounded border px-2 py-1 text-sm"
              value={auth.password}
              onChange={(e) => update({ password: e.target.value })}
            />
          </div>
        </>
      )}

      {auth.type === "oauth2_cc" && (
        <>
          <div>
            <label htmlFor="oauth-token-url" className="text-xs text-gray-500">
              Token URL
            </label>
            <input
              id="oauth-token-url"
              type="text"
              className="mt-1 w-full rounded border px-2 py-1 text-sm font-mono"
              value={auth.token_url}
              placeholder="https://auth.example.com/token"
              onChange={(e) => update({ token_url: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="oauth-client-id" className="text-xs text-gray-500">
              Client ID
            </label>
            <input
              id="oauth-client-id"
              type="text"
              className="mt-1 w-full rounded border px-2 py-1 text-sm font-mono"
              value={auth.client_id}
              onChange={(e) => update({ client_id: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="oauth-client-secret" className="text-xs text-gray-500">
              Client Secret
            </label>
            <input
              id="oauth-client-secret"
              type="password"
              className="mt-1 w-full rounded border px-2 py-1 text-sm font-mono"
              value={auth.client_secret}
              onChange={(e) => update({ client_secret: e.target.value })}
            />
          </div>
          <div>
            <label htmlFor="oauth-scope" className="text-xs text-gray-500">
              Scope
            </label>
            <input
              id="oauth-scope"
              type="text"
              className="mt-1 w-full rounded border px-2 py-1 text-sm font-mono"
              value={auth.scope}
              placeholder="optional"
              onChange={(e) => update({ scope: e.target.value })}
            />
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Run full check**

```bash
make check
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/request/AuthTab.tsx
git commit -m "feat: add OAuth 2.0 client credentials form to AuthTab"
```

---

### Task 9: Frontend CookiesTab

**Files:**
- Modify: `frontend/src/components/request/CookiesTab.tsx`

- [ ] **Step 1: Update `CookiesTab.tsx`**

Replace the entire file with:

```tsx
import { useClearCookies, useCookies } from "../../api/cookies";
import { KeyValueTable } from "./KeyValueTable";
import { useRequestStore } from "../../store/requestStore";
import type { CookieMode } from "../../types";

export function CookiesTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const cookieConfig = current?.frontmatter.cookies ?? { mode: "session" as CookieMode, cookies: {} };

  const { data: allCookies } = useCookies();
  const clearMutation = useClearCookies();

  const hostname = (() => {
    try {
      return new URL(current?.frontmatter.url ?? "").hostname;
    } catch {
      return "";
    }
  })();

  const sessionCookies: Record<string, string> =
    hostname && allCookies ? (allCookies[hostname] ?? {}) : {};

  return (
    <div className="p-3 flex flex-col gap-4">
      <div>
        <label htmlFor="cookie-mode" className="text-xs text-gray-500">
          Cookie mode
        </label>
        <select
          id="cookie-mode"
          className="mt-1 w-48 rounded border px-2 py-1 text-sm"
          value={cookieConfig.mode}
          onChange={(e) =>
            patch({ cookies: { ...cookieConfig, mode: e.target.value as CookieMode } })
          }
        >
          <option value="session">Session (auto)</option>
          <option value="disabled">Disabled</option>
          <option value="explicit">Explicit</option>
        </select>
      </div>

      {cookieConfig.mode === "explicit" && (
        <div>
          <p className="text-xs text-gray-500 mb-1">Cookies to send</p>
          <KeyValueTable
            entries={cookieConfig.cookies}
            onChange={(cookies) => patch({ cookies: { ...cookieConfig, cookies } })}
            keyPlaceholder="Cookie name"
            valuePlaceholder="Value"
          />
        </div>
      )}

      {cookieConfig.mode === "session" && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs text-gray-500">Session cookies for {hostname || "this host"}</p>
            <button
              type="button"
              className="text-xs text-gray-400 hover:text-red-500"
              onClick={() => clearMutation.mutate()}
            >
              Clear all
            </button>
          </div>
          {Object.keys(sessionCookies).length === 0 ? (
            <p className="text-xs text-gray-400 italic">
              {hostname ? `No session cookies for ${hostname}` : "Enter a URL to see session cookies"}
            </p>
          ) : (
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-gray-400 text-left">
                  <th className="pr-4 pb-1 font-normal">Name</th>
                  <th className="pb-1 font-normal">Value</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(sessionCookies).map(([name, value]) => (
                  <tr key={name} className="border-t border-gray-100">
                    <td className="pr-4 py-1 text-gray-700">{name}</td>
                    <td className="py-1 text-gray-500 truncate max-w-0">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Run full check**

```bash
make check
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/request/CookiesTab.tsx
git commit -m "feat: implement CookiesTab with mode selector, explicit editor, and session jar viewer"
```

---

## Final verification

- [ ] **Run the full test suite**

```bash
make check
```

Expected: ruff + pyright + tsc + pytest all pass. Test count should be around 230+ (207 existing + ~23 new).

- [ ] **Update TODO.md** to reflect Phase 9 complete and Phase 10 as current sprint.
