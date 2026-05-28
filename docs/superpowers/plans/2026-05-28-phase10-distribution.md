# Phase 10 — Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add distribution infrastructure (Homebrew formula, `make dist`, MkDocs docs site) and fix two deferred Phase 9 items (expired cookie row cleanup + OAuth credential variable substitution).

**Architecture:** Two clean Python fixes in `drummer/core` (cookie deletion path + OAuth field substitution in `variables.py`), standalone packaging scripts in `scripts/`, docs content in `docs/site/` served by MkDocs Material deployed via GitHub Actions, and an in-repo Homebrew formula template in `formula/`.

**Tech Stack:** Python 3.12, SQLAlchemy async, hatch (build), MkDocs Material 9.5, GitHub Actions

---

## File Map

| File | Change |
|---|---|
| `tests/unit/test_cookies_persistence.py` | Add `delete` to `_MockPersistence`; add 2 new tests |
| `drummer/core/cookies.py` | Add `delete` to `CookiePersistenceProtocol`; update `update_from_response` |
| `drummer/api/db/cookie_persistence.py` | Add `delete` method |
| `drummer/api/db/session.py` | Import `text`; add `PRAGMA auto_vacuum` to `init_db` |
| `tests/integration/test_cookies_persistence.py` | Add 1 new integration test |
| `drummer/core/variables.py` | Import `AuthConfig`; add `OAUTH2_CC` substitution branch; change `auth=fm.auth` → `auth=auth` |
| `tests/unit/test_variables.py` | Add 2 new tests |
| `pyproject.toml` | Add `hatch`, `mkdocs-material` to dev deps; add `scripts/**` per-file-ignores; add `artifacts` for static build output |
| `Makefile` | Add `MKDOCS`, `HATCH` vars; add `dist`, `docs`, `docs-serve` targets; update `.PHONY` |
| `.gitignore` | Add `site/` |
| `formula/drummer.rb` | **New** — Homebrew formula with placeholder SHA/URL |
| `scripts/dist.py` | **New** — wheel build helper: patch formula SHA, print release checklist |
| `mkdocs.yml` | **New** — MkDocs site config |
| `docs/site/index.md` | **New** |
| `docs/site/getting-started.md` | **New** |
| `docs/site/cli-reference.md` | **New** |
| `docs/site/scripting-api.md` | **New** |
| `docs/site/mcp-tools.md` | **New** |
| `docs/site/attribution.md` | **New** |
| `drummer/mock/DATA_ATTRIBUTION.md` | **New** — attribution file bundled with package |
| `.github/workflows/docs.yml` | **New** — GitHub Pages deployment |

---

## Task 1: Expired cookie row deletion — unit level

**Files:**
- Modify: `tests/unit/test_cookies_persistence.py`
- Modify: `drummer/core/cookies.py`

- [ ] **Step 1: Write the failing tests**

Add to the end of `tests/unit/test_cookies_persistence.py`:

```python
async def test_expired_cookie_calls_delete_not_save() -> None:
    mock = _MockPersistence()
    jar = CookieJar(persistence=mock)
    past = (datetime.now(UTC) - timedelta(seconds=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    await jar.update_from_response("http://api.example.com/", [f"session=abc123; expires={past}"])
    assert mock.deleted == [("api.example.com", "session")]
    assert mock.saved == []


async def test_max_age_zero_calls_delete_not_save() -> None:
    mock = _MockPersistence()
    jar = CookieJar(persistence=mock)
    await jar.update_from_response("http://api.example.com/", ["session=abc123"])
    await jar.update_from_response("http://api.example.com/", ["session=; max-age=0"])
    assert ("api.example.com", "session") in mock.deleted
```

- [ ] **Step 2: Run to verify they fail**

```bash
venv/bin/pytest tests/unit/test_cookies_persistence.py::test_expired_cookie_calls_delete_not_save tests/unit/test_cookies_persistence.py::test_max_age_zero_calls_delete_not_save -v
```

Expected: FAIL — `AttributeError: '_MockPersistence' object has no attribute 'deleted'`

- [ ] **Step 3: Update `_MockPersistence`, `CookiePersistenceProtocol`, and `CookieJar.update_from_response`**

Replace `_MockPersistence` in `tests/unit/test_cookies_persistence.py` (lines 8–25):

```python
class _MockPersistence:
    def __init__(self) -> None:
        self.saved: list[tuple[str, str, str, datetime | None]] = []
        self.deleted: list[tuple[str, str]] = []
        self.cleared = False
        self.data: dict[str, dict[str, tuple[str, datetime | None]]] = {}

    async def load(self) -> dict[str, dict[str, tuple[str, datetime | None]]]:
        return self.data

    async def save(self, hostname: str, name: str, value: str, expires_at: datetime | None) -> None:
        self.saved.append((hostname, name, value, expires_at))
        if hostname not in self.data:
            self.data[hostname] = {}
        self.data[hostname][name] = (value, expires_at)

    async def delete(self, hostname: str, name: str) -> None:
        self.deleted.append((hostname, name))
        if hostname in self.data:
            self.data[hostname].pop(name, None)

    async def clear(self) -> None:
        self.cleared = True
        self.data.clear()
```

Replace `CookiePersistenceProtocol` in `drummer/core/cookies.py` (lines 11–16):

```python
class CookiePersistenceProtocol(Protocol):
    async def load(self) -> dict[str, dict[str, tuple[str, datetime | None]]]: ...
    async def save(
        self, hostname: str, name: str, value: str, expires_at: datetime | None
    ) -> None: ...
    async def delete(self, hostname: str, name: str) -> None: ...
    async def clear(self) -> None: ...
```

Replace the inner loop body in `CookieJar.update_from_response` in `drummer/core/cookies.py` (lines 70–79):

```python
        for header in set_cookie_headers:
            name, value, expires_at = _parse_set_cookie(header, now)
            if not name:
                continue
            if expires_at is not None and expires_at <= now:
                self._store[hostname].pop(name, None)
                if self._persistence is not None:
                    await self._persistence.delete(hostname, name)
            else:
                self._store[hostname][name] = (value, expires_at)
                if self._persistence is not None:
                    await self._persistence.save(hostname, name, value, expires_at)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/unit/test_cookies_persistence.py -v
```

Expected: all PASS (including the 2 new tests and all 8 existing tests)

- [ ] **Step 5: Run full check**

```bash
make check
```

Expected: all 244+ tests pass, no lint errors

- [ ] **Step 6: Commit**

```bash
git add tests/unit/test_cookies_persistence.py drummer/core/cookies.py
git commit -m "fix: delete expired cookies from persistence instead of saving"
```

---

## Task 2: Expired cookie deletion — SQLite impl + auto-vacuum + integration test

**Files:**
- Modify: `drummer/api/db/cookie_persistence.py`
- Modify: `drummer/api/db/session.py`
- Modify: `tests/integration/test_cookies_persistence.py`

- [ ] **Step 1: Write the failing integration test**

Add to the end of `tests/integration/test_cookies_persistence.py`:

```python
async def test_expired_cookie_deleted_from_db(tmp_path: Path) -> None:
    db_url = _db_url(tmp_path)
    await init_db(db_url)
    factory = async_session_factory(db_url)

    jar1 = CookieJar(persistence=CookiePersistence(factory))
    future = (datetime.now(UTC) + timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    await jar1.update_from_response(
        "http://api.example.com/", [f"session=abc123; expires={future}"]
    )
    await jar1.update_from_response("http://api.example.com/", ["session=; max-age=0"])

    jar2 = CookieJar(persistence=CookiePersistence(factory))
    await jar2.load_from_db()
    cookies = jar2.cookies_for_request("http://api.example.com/", CookieMode.SESSION, {})
    assert "session" not in cookies
```

Make sure the imports at the top of `tests/integration/test_cookies_persistence.py` include `timedelta`:

```python
from datetime import UTC, datetime, timedelta
from pathlib import Path

from drummer.api.db.cookie_persistence import CookiePersistence
from drummer.api.db.session import async_session_factory, init_db
from drummer.core.cookies import CookieJar
from drummer.core.storage.formats import CookieMode
```

- [ ] **Step 2: Run to verify it fails**

```bash
venv/bin/pytest tests/integration/test_cookies_persistence.py::test_expired_cookie_deleted_from_db -v
```

Expected: FAIL — `AttributeError: 'CookiePersistence' object has no attribute 'delete'`

- [ ] **Step 3: Add `delete` to `CookiePersistence`**

Replace `drummer/api/db/cookie_persistence.py` in full:

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

    async def save(self, hostname: str, name: str, value: str, expires_at: datetime | None) -> None:
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

    async def delete(self, hostname: str, name: str) -> None:
        async with self._factory() as session:
            await session.execute(
                delete(CookieRecord).where(
                    CookieRecord.hostname == hostname,
                    CookieRecord.name == name,
                )
            )
            await session.commit()

    async def clear(self) -> None:
        async with self._factory() as session:
            await session.execute(delete(CookieRecord))
            await session.commit()
```

Note: `delete` in the method body refers to the module-level `from sqlalchemy import delete` import, not `self.delete`. This is valid Python — method names only shadow module-level names when accessed without `self`.

- [ ] **Step 4: Add `PRAGMA auto_vacuum` to `init_db`**

Replace `drummer/api/db/session.py` in full:

```python
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from drummer.api.db.models import Base

_SQLITE_PREFIX = "sqlite+aiosqlite:///"


def async_session_factory(db_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(db_url)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(db_url: str) -> None:
    if db_url.startswith(_SQLITE_PREFIX):
        Path(db_url[len(_SQLITE_PREFIX) :]).parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA auto_vacuum = FULL"))
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
```

`PRAGMA auto_vacuum = FULL` causes SQLite to automatically reclaim page space when rows are deleted. It takes effect immediately for new databases. On existing databases, it requires a `VACUUM` to change the mode — but since the `delete()` fix stops future accumulation regardless, this is acceptable.

- [ ] **Step 5: Run integration tests to verify they pass**

```bash
venv/bin/pytest tests/integration/test_cookies_persistence.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 6: Run full check**

```bash
make check
```

Expected: all tests pass, no lint errors

- [ ] **Step 7: Commit**

```bash
git add drummer/api/db/cookie_persistence.py drummer/api/db/session.py tests/integration/test_cookies_persistence.py
git commit -m "fix: add SQLite delete path for expired cookies; enable auto_vacuum"
```

---

## Task 3: OAuth credential variable substitution

**Files:**
- Modify: `drummer/core/variables.py`
- Modify: `tests/unit/test_variables.py`

- [ ] **Step 1: Write the failing tests**

Add to the end of `tests/unit/test_variables.py`:

```python
def test_resolve_oauth2_cc_fields_substituted(tmp_path: Path) -> None:
    fm = RequestFrontmatter(
        name="Test",
        url="https://api.example.com",
        auth=AuthConfig(
            type=AuthType.OAUTH2_CC,
            token_url="{{token_url}}",
            client_id="{{client_id}}",
            client_secret="{{client_secret}}",
            scope="{{scope}}",
        ),
    )
    rf = RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")
    env = {
        "token_url": "https://auth.example.com/token",
        "client_id": "my-client",
        "client_secret": "s3cr3t",
        "scope": "read write",
    }
    resolved = resolve(rf, env)
    assert resolved.auth.token_url == "https://auth.example.com/token"
    assert resolved.auth.client_id == "my-client"
    assert resolved.auth.client_secret == "s3cr3t"
    assert resolved.auth.scope == "read write"
    assert resolved.warnings == []


def test_resolve_oauth2_cc_unresolved_fields_warn(tmp_path: Path) -> None:
    fm = RequestFrontmatter(
        name="Test",
        url="https://api.example.com",
        auth=AuthConfig(
            type=AuthType.OAUTH2_CC,
            token_url="https://auth.example.com/token",
            client_id="{{client_id}}",
            client_secret="{{client_secret}}",
            scope="",
        ),
    )
    rf = RequestFile(frontmatter=fm, body="", path=tmp_path / "req.md")
    resolved = resolve(rf, {})
    assert "client_id" in resolved.warnings
    assert "client_secret" in resolved.warnings
    assert resolved.auth.client_id == "{{client_id}}"
    assert resolved.auth.client_secret == "{{client_secret}}"
```

Check existing imports at the top of `tests/unit/test_variables.py` — `AuthConfig` and `AuthType` should already be imported:

```python
from drummer.core.storage.formats import AuthConfig, AuthType, RequestFile, RequestFrontmatter
```

- [ ] **Step 2: Run to verify they fail**

```bash
venv/bin/pytest tests/unit/test_variables.py::test_resolve_oauth2_cc_fields_substituted tests/unit/test_variables.py::test_resolve_oauth2_cc_unresolved_fields_warn -v
```

Expected: FAIL — resolved OAuth fields still contain `{{variable}}` syntax (substitution not yet applied)

- [ ] **Step 3: Update `drummer/core/variables.py`**

Replace the file in full:

```python
import base64
import re

from drummer.core.engine import ResolvedRequest
from drummer.core.storage.formats import AuthConfig, AuthType, GraphQLConfig, RequestFile

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")
_SCRIPT_TIMEOUT_DEFAULT = 5000


def substitute(text: str, env: dict[str, str]) -> tuple[str, list[str]]:
    warnings: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in env:
            return env[name]
        warnings.append(name)
        return match.group(0)

    return _VAR_RE.sub(_replace, text), warnings


def resolve(
    request_file: RequestFile, env: dict[str, str], project_timeout_ms: int | None = None
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
    elif auth.type == AuthType.OAUTH2_CC:
        auth = AuthConfig(
            type=auth.type,
            token_url=sub(auth.token_url),
            client_id=sub(auth.client_id),
            client_secret=sub(auth.client_secret),
            scope=sub(auth.scope),
        )

    effective_timeout = fm.script_timeout_ms or project_timeout_ms or _SCRIPT_TIMEOUT_DEFAULT

    graphql_resolved: GraphQLConfig | None = None
    if fm.graphql is not None:
        graphql_resolved = GraphQLConfig(
            query=sub(fm.graphql.query), variables=fm.graphql.variables
        )

    return ResolvedRequest(
        name=fm.name,
        method=fm.method,
        url=url,
        headers=headers,
        params=params,
        body=body,
        encoding=fm.encoding,
        cookies=fm.cookies,
        auth=auth,
        warnings=sorted(seen),
        pre_script=fm.pre_script,
        post_script=fm.post_script,
        script_timeout_ms=effective_timeout,
        variables=dict(env),
        graphql=graphql_resolved,
    )
```

Key changes:
- Added `AuthConfig` to the import from `drummer.core.storage.formats`
- Added `elif auth.type == AuthType.OAUTH2_CC:` branch that rebuilds `AuthConfig` with substituted fields
- Changed `auth=fm.auth` → `auth=auth` in the `return` statement so the substituted version is passed through

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/unit/test_variables.py -v
```

Expected: all 15+ tests PASS

- [ ] **Step 5: Run full check**

```bash
make check
```

Expected: all tests pass, no lint errors

- [ ] **Step 6: Commit**

```bash
git add drummer/core/variables.py tests/unit/test_variables.py
git commit -m "fix: apply variable substitution to OAuth 2.0 credential fields"
```

---

## Task 4: Homebrew formula

**Files:**
- Create: `formula/drummer.rb`

- [ ] **Step 1: Create `formula/drummer.rb`**

```bash
mkdir -p formula
```

Write `formula/drummer.rb`:

```ruby
class Drummer < Formula
  include Language::Python::Virtualenv

  desc "Local, standalone REST client — free alternative to Postman/Insomnia/Bruno"
  homepage "https://github.com/ceautery/drummer"

  # TODO: update url and sha256 when a GitHub release exists
  # Run `make dist` after tagging a release to generate the correct sha256.
  url "https://github.com/ceautery/drummer/releases/download/v0.1.0/drummer-0.1.0-py3-none-any.whl"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"

  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"drummer", "--version"
  end
end
```

`virtualenv_install_with_resources` creates a managed virtualenv, installs the downloaded wheel and its declared dependencies into it, and links the `drummer` entry point into `bin/`.

The `sha256` placeholder will be overwritten by `make dist`. The `url` must be updated manually to a real GitHub release asset URL before publishing the tap.

- [ ] **Step 2: Run full check**

```bash
make check
```

Expected: all tests pass, no lint errors (the `.rb` file is not checked by ruff/pyright)

- [ ] **Step 3: Commit**

```bash
git add formula/drummer.rb
git commit -m "feat: add Homebrew formula template"
```

---

## Task 5: `make dist` pipeline

**Files:**
- Modify: `pyproject.toml`
- Create: `scripts/dist.py`
- Modify: `Makefile`

- [ ] **Step 1: Update `pyproject.toml`**

Replace the `[project.optional-dependencies]` section and `[tool.hatch.build.targets.wheel]` and `[tool.ruff.lint.per-file-ignores]` sections. Show only the changed sections (the rest of pyproject.toml is unchanged):

`[project.optional-dependencies]` — add `hatch`:
```toml
[project.optional-dependencies]
dev = [
    "ruff>=0.5",
    "pyright>=1.1",
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "pytest-playwright>=0.5",
    "hatch>=1.12",
]
```

`[tool.hatch.build.targets.wheel]` — add `artifacts` so the compiled frontend is included in the wheel even though `drummer/api/static/` is gitignored:
```toml
[tool.hatch.build.targets.wheel]
packages = ["drummer"]
artifacts = ["drummer/api/static"]
```

`[tool.ruff.lint.per-file-ignores]` — add `scripts/**`:
```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "S105", "S106", "ANN", "S603"]
"drummer/cli.py" = ["FBT", "RSE102"]
"stubs/**" = ["ANN401", "N818", "UP035"]
"scripts/**" = ["T201", "INP001", "ANN"]
```

`T201` = print statement, `INP001` = implicit namespace package (no `__init__.py` in `scripts/`), `ANN` = missing type annotations.

- [ ] **Step 2: Create `scripts/dist.py`**

```python
"""Update formula/drummer.rb with the SHA256 of the latest wheel in dist/."""
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DIST_DIR = REPO_ROOT / "dist"
FORMULA = REPO_ROOT / "formula" / "drummer.rb"
_SHA_RE = re.compile(r'(\s*sha256 ")[^"]*(")')


def main() -> None:
    wheels = sorted(DIST_DIR.glob("drummer-*.whl"))
    if not wheels:
        print("No wheel found in dist/. Run 'hatch build' first.", file=sys.stderr)
        sys.exit(1)

    wheel = wheels[-1]
    sha256 = hashlib.sha256(wheel.read_bytes()).hexdigest()

    formula_text = FORMULA.read_text()
    updated, n_subs = _SHA_RE.subn(rf'\g<1>{sha256}\g<2>', formula_text, count=1)
    if n_subs == 0:
        print("Warning: sha256 line not found in formula — no changes made.", file=sys.stderr)
        sys.exit(1)

    FORMULA.write_text(updated)

    print(f"Wheel:   {wheel.name}")
    print(f"SHA256:  {sha256}")
    print(f"Formula: formula/drummer.rb updated")
    print()
    print("Release checklist:")
    print("  [ ] Tag a release: git tag v<version> && git push origin v<version>")
    print("  [ ] Upload dist/*.whl as a GitHub release asset")
    print("  [ ] Update formula url to the release asset URL")
    print("  [ ] Copy formula/drummer.rb -> homebrew-drummer/Formula/drummer.rb")
    print("  [ ] Push tap repo")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Update `Makefile`**

Replace the `Makefile` in full:

```makefile
VENV    := $(CURDIR)/venv
PYTHON  := $(VENV)/bin/python
RUFF    := $(VENV)/bin/ruff
PYRIGHT := $(VENV)/bin/pyright
PYTEST  := $(VENV)/bin/pytest
MKDOCS  := $(VENV)/bin/mkdocs
HATCH   := $(VENV)/bin/hatch
NPM     := npm

PROJECT ?=

.PHONY: install lint format check test test-file test-e2e dev e2e build-frontend dist docs docs-serve

install:
	pip install -e ".[dev]"
	cd frontend && $(NPM) install

lint:
	$(RUFF) check .
	$(RUFF) format --check .
	$(PYRIGHT) drummer
	cd frontend && $(NPM) run check

format:
	$(RUFF) format .
	$(RUFF) check --fix .
	cd frontend && $(NPM) run check:fix

test:
	$(PYTEST) tests/unit tests/integration -q

test-file:
	$(PYTEST) $(FILE) -v

test-e2e:
	$(PYTEST) tests/e2e -v

check: lint test

build-frontend:
	cd frontend && $(NPM) run build

dist: build-frontend
	$(HATCH) build
	$(PYTHON) scripts/dist.py

docs:
	$(MKDOCS) build

docs-serve:
	$(MKDOCS) serve

dev:
ifndef PROJECT
	$(error Usage: make dev PROJECT=/path/to/your/project)
endif
	trap 'kill 0' EXIT; (cd frontend && $(NPM) run dev) & $(PYTHON) -m drummer.cli serve --project $(PROJECT)

e2e: build-frontend test-e2e
```

- [ ] **Step 4: Install updated dependencies**

```bash
pip install -e ".[dev]"
```

Expected: `hatch` appears in the venv at `venv/bin/hatch`

- [ ] **Step 5: Run full check**

```bash
make check
```

Expected: all tests pass, no lint errors (including `scripts/dist.py`)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml scripts/dist.py Makefile
git commit -m "feat: add make dist pipeline with formula SHA patcher"
```

---

## Task 6: MkDocs setup

**Files:**
- Modify: `pyproject.toml`
- Create: `mkdocs.yml`
- Modify: `.gitignore`
- Modify: `Makefile` (already updated in Task 5 — no further changes needed)

- [ ] **Step 1: Add `mkdocs-material` to `pyproject.toml` dev deps**

In `[project.optional-dependencies]`, add `mkdocs-material` after `hatch`:

```toml
[project.optional-dependencies]
dev = [
    "ruff>=0.5",
    "pyright>=1.1",
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "pytest-playwright>=0.5",
    "hatch>=1.12",
    "mkdocs-material>=9.5",
]
```

- [ ] **Step 2: Create `mkdocs.yml`**

```yaml
site_name: Drummer
site_description: A local, standalone REST client — free alternative to Postman/Insomnia/Bruno
site_url: https://ceautery.github.io/drummer/
repo_url: https://github.com/ceautery/drummer
repo_name: ceautery/drummer

docs_dir: docs/site
site_dir: site

theme:
  name: material
  palette:
    - scheme: default
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - navigation.tabs
    - navigation.sections
    - content.code.copy

nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - CLI Reference: cli-reference.md
  - Scripting API: scripting-api.md
  - MCP Tools: mcp-tools.md
  - Attribution: attribution.md

markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.superfences
  - admonition
  - attr_list
```

- [ ] **Step 3: Add `site/` to `.gitignore`**

Add to the end of `.gitignore`:

```
# MkDocs build output
site/
```

- [ ] **Step 4: Install updated dependencies**

```bash
pip install -e ".[dev]"
```

Expected: `mkdocs` appears in the venv at `venv/bin/mkdocs`

- [ ] **Step 5: Create `docs/site/` with a placeholder `index.md`**

```bash
mkdir -p docs/site
```

Write `docs/site/index.md`:

```markdown
# Drummer

Placeholder — full content coming in the next task.
```

- [ ] **Step 6: Verify MkDocs builds**

```bash
make docs
```

Expected: `site/` directory created with `index.html` inside; no errors

- [ ] **Step 7: Run full check**

```bash
make check
```

Expected: all tests pass, no lint errors

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml mkdocs.yml .gitignore docs/site/index.md
git commit -m "feat: add MkDocs Material setup and site skeleton"
```

---

## Task 7: Docs content

**Files:**
- Modify: `docs/site/index.md`
- Create: `docs/site/getting-started.md`
- Create: `docs/site/cli-reference.md`
- Create: `docs/site/scripting-api.md`
- Create: `docs/site/mcp-tools.md`
- Create: `docs/site/attribution.md`
- Create: `drummer/mock/DATA_ATTRIBUTION.md`

- [ ] **Step 1: Replace `docs/site/index.md`**

```markdown
# Drummer

A local, standalone REST client — free and open-source alternative to Postman, Insomnia, and Bruno.

- **No account** — runs entirely on your machine
- **No subscription** — free forever
- **No phone-home** — your data stays local
- **Git-friendly** — request files are plain Markdown with YAML frontmatter, fully diffable

## Install

**Homebrew (macOS):**

```bash
brew tap ceautery/drummer
brew install drummer
```

**pip:**

```bash
pip install drummer
```

## Quick start

```bash
drummer serve --project /path/to/your/project
```

Drummer opens in your browser at `http://localhost:8000`.

## Links

- [Getting Started](getting-started.md)
- [CLI Reference](cli-reference.md)
- [Scripting API](scripting-api.md)
- [MCP Tools](mcp-tools.md)
- [Source on GitHub](https://github.com/ceautery/drummer)
```

- [ ] **Step 2: Create `docs/site/getting-started.md`**

```markdown
# Getting Started

## Requirements

- macOS or Linux
- Python 3.12+

## Install

**Homebrew (macOS):**

```bash
brew tap ceautery/drummer
brew install drummer
```

**pip:**

```bash
pip install drummer
```

## Create a project

A Drummer project is a folder with a `.drummer/` directory. Create one by hand:

```
my-api/
├── .drummer/
│   ├── project.yaml
│   └── environments/
│       └── local.yaml
└── list-users.md
```

**`.drummer/project.yaml`**

```yaml
name: My API
version: "1"
default_environment: local
```

**`.drummer/environments/local.yaml`**

```yaml
name: local
variables:
  base_url: https://jsonplaceholder.typicode.com
```

**`list-users.md`**

```markdown
---
name: List Users
method: GET
url: "{{base_url}}/users"
---
```

## Start Drummer

```bash
drummer serve --project /path/to/my-api
```

Drummer starts on port 8000. Open `http://localhost:8000` in your browser. Select your environment in the sidebar, click **Send**, and see the response.

## Built-in tutorial

Run `drummer serve` without a `--project` flag to open the built-in tutorial, which walks through all of Drummer's features using an offline mock API.

## What's next

- [CLI Reference](cli-reference.md) — all commands and flags
- [Scripting API](scripting-api.md) — pre/post-request JavaScript
- [MCP Tools](mcp-tools.md) — connect Claude to Drummer
```

- [ ] **Step 3: Create `docs/site/cli-reference.md`**

```markdown
# CLI Reference

## drummer serve

Start the Drummer server and open it in the browser.

```bash
drummer serve [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--project PATH` | none | Path to a Drummer project folder |
| `--port INTEGER` | 8000 | Port to listen on |
| `--host TEXT` | 127.0.0.1 | Host address to bind to |

**Examples:**

```bash
# Open with no project (shows built-in tutorial)
drummer serve

# Open a specific project
drummer serve --project ~/projects/my-api

# Custom port
drummer serve --port 9000 --project ~/projects/my-api
```

---

## drummer new

Create a new Drummer project at the given path.

```bash
drummer new PATH
```

Creates a `.drummer/` directory with `project.yaml` and a default `local` environment at `PATH`.

---

## drummer export

Export a Drummer project as a zip file for sharing.

```bash
drummer export PATH
```

---

## drummer mcp

Print MCP server connection information.

```bash
drummer mcp
```

Outputs the URL and port to configure in Claude's MCP settings, and lists all available tools.

---

## Global flags

| Flag | Description |
|---|---|
| `--version` / `-V` | Print version and exit |
| `--attribution` | Print dataset attribution (Metropolitan Museum of Art) and exit |
| `--help` | Show help for any command |
```

- [ ] **Step 4: Create `docs/site/scripting-api.md`**

```markdown
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
```

- [ ] **Step 5: Create `docs/site/mcp-tools.md`**

```markdown
# MCP Tools

Drummer exposes a Model Context Protocol (MCP) server so Claude can send requests, inspect responses, and manage environments directly.

## Setup

1. Start Drummer: `drummer serve`
2. Add to your Claude MCP configuration:

```json
{
  "mcpServers": {
    "drummer": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Run `drummer mcp` to confirm the URL and list available tools.

## Available tools

| Tool | Description |
|---|---|
| `list_projects` | List all known projects with metadata |
| `list_requests` | Get the request tree for a project |
| `get_request` | Get the parsed definition of a request |
| `create_request` | Create a new request file |
| `update_request` | Update fields in an existing request |
| `send_request` | Fire a request; returns status, headers, body, timing, script output |
| `get_history` | Recent response history for a request |
| `list_environments` | List environments for a project |
| `get_variables` | Get variables for a named environment |
| `set_variable` | Set a variable in the active environment |
| `switch_environment` | Change the active environment |
| `clear_cookies` | Clear the session cookie store |

## Example workflow

```
list_projects
→ [{ "name": "My API", "id": "my-api" }]

list_requests { "project_id": "my-api" }
→ [{ "path": "users/list-users.md", "name": "List Users" }]

send_request { "project_id": "my-api", "path": "users/list-users.md" }
→ { "status_code": 200, "elapsed_ms": 142, "body": "[{\"id\":1,...}]" }

set_variable { "project_id": "my-api", "env": "local", "key": "base_url", "value": "https://staging.example.com" }

send_request { "project_id": "my-api", "path": "users/list-users.md" }
→ { "status_code": 200, "elapsed_ms": 98, "body": "[...]" }
```
```

- [ ] **Step 6: Create `docs/site/attribution.md`**

```markdown
# Attribution

## Metropolitan Museum of Art Open Access

Drummer's built-in tutorial and mock server include data from the Metropolitan Museum of Art Open Access collection.

**License:** Creative Commons Zero (CC0) — no rights reserved
**Source:** [metmuseum.org/about-the-met/policies-and-documents/open-access](https://www.metmuseum.org/about-the-met/policies-and-documents/open-access)

The Met makes its Open Access data available for unrestricted commercial and noncommercial use without requiring permission from the Museum.

This data is used here for educational and demonstration purposes only.
```

- [ ] **Step 7: Create `drummer/mock/DATA_ATTRIBUTION.md`**

```markdown
# Data Attribution

Drummer includes data from the Metropolitan Museum of Art Open Access collection.

License: Creative Commons Zero (CC0) — no rights reserved
Source: https://www.metmuseum.org/about-the-met/policies-and-documents/open-access

The Met makes its Open Access data available for unrestricted commercial and noncommercial use
without requiring permission from the Museum.
```

- [ ] **Step 8: Verify docs build cleanly**

```bash
make docs
```

Expected: `site/` populated with 6 HTML pages, no warnings or errors

- [ ] **Step 9: Run full check**

```bash
make check
```

Expected: all tests pass, no lint errors

- [ ] **Step 10: Commit**

```bash
git add docs/site/ drummer/mock/DATA_ATTRIBUTION.md
git commit -m "docs: add MkDocs site content (6 pages)"
```

---

## Task 8: GitHub Actions docs deployment

**Files:**
- Create: `.github/workflows/docs.yml`

- [ ] **Step 1: Create `.github/workflows/docs.yml`**

```yaml
name: Docs

on:
  push:
    branches: [main]
    paths:
      - "docs/site/**"
      - "mkdocs.yml"

jobs:
  deploy:
    name: Deploy to GitHub Pages
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Create venv
        run: python -m venv venv

      - name: Install docs dependencies
        run: venv/bin/pip install mkdocs-material

      - name: Deploy docs
        run: venv/bin/mkdocs gh-deploy --force
```

The workflow triggers only when `docs/site/**` or `mkdocs.yml` changes, keeping CI fast for code-only commits. `gh-deploy --force` builds the site and pushes it to the `gh-pages` branch. GitHub Pages serves it at `https://ceautery.github.io/drummer/`.

Enable GitHub Pages in the repo settings (Settings → Pages → Source: "Deploy from a branch" → branch: `gh-pages`, folder: `/ (root)`) after the first deploy runs.

- [ ] **Step 2: Run full check**

```bash
make check
```

Expected: all tests pass, no lint errors

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/docs.yml
git commit -m "ci: add GitHub Actions workflow for MkDocs GitHub Pages deployment"
```

---

## Final verification

After all 8 tasks are complete:

```bash
make check
```

Expected output:
```
All checks passed.
N passed, 0 warnings
```

where N ≥ 248 (244 existing + 2 cookie deletion + 1 cookie integration + 2 OAuth substitution = 249 minimum).

Confirm the formula was patched (skip the actual wheel build if you don't want to run `npm run build` in full):

```bash
grep sha256 formula/drummer.rb
```

Expected: still the placeholder `0000...` (patched only by `make dist` which requires a frontend build).
