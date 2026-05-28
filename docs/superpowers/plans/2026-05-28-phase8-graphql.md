# Phase 8: GraphQL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full GraphQL support — data model changes, introspection proxy endpoint, and a three-sub-tab editor (Query / Variables / Schema) with schema-aware autocomplete.

**Architecture:** Python receives `graphql` frontmatter, synthesizes the JSON body in the send pipeline. A new `/api/graphql/introspect` route proxies introspection queries server-side to avoid browser CORS. The frontend adds `GraphQLTab` + `SchemaExplorer` components wired into `BodyTab`.

**Tech Stack:** Python/Pydantic (data model), httpx (introspection proxy), FastAPI (route), React + CodeMirror 6 (`cm6-graphql`, `@codemirror/lang-json`), `graphql` JS package (`buildClientSchema`)

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `drummer/core/storage/formats.py` | Modify | `GraphQLConfig.variables: dict[str, Any]` |
| `drummer/core/engine.py` | Modify | `ResolvedRequest.graphql` field; GraphQL body synthesis in `send()` |
| `drummer/core/variables.py` | Modify | Pass `graphql` through `resolve()`, substitute vars in query |
| `tests/unit/test_graphql_engine.py` | Create | Engine + resolve unit tests |
| `drummer/api/routes/graphql_routes.py` | Create | `POST /graphql/introspect` route |
| `drummer/api/app.py` | Modify | Mount graphql router |
| `tests/unit/test_graphql_introspect.py` | Create | Pydantic model unit tests |
| `tests/integration/test_graphql_introspect.py` | Create | Introspect route integration tests |
| `tests/integration/test_graphql_send.py` | Create | Send pipeline integration tests |
| `frontend/src/types.ts` | Modify | `GraphQLConfig` interface; `graphql?` on `RequestFrontmatter` |
| `frontend/src/components/request/SchemaExplorer.tsx` | Create | Type explorer tree |
| `frontend/src/components/request/GraphQLTab.tsx` | Create | Three-sub-tab GraphQL editor |
| `frontend/src/components/request/BodyTab.tsx` | Modify | Enable graphql button; mode init; render `GraphQLTab` |

---

## Task 1: Python data model + send pipeline

**Files:**
- Modify: `drummer/core/storage/formats.py`
- Modify: `drummer/core/engine.py`
- Modify: `drummer/core/variables.py`
- Create: `tests/unit/test_graphql_engine.py`

---

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_graphql_engine.py`:

```python
import json

import httpx
import pytest
from pydantic import ValidationError

from drummer.core.cookies import CookieJar
from drummer.core.engine import ResolvedRequest, send
from drummer.core.storage.formats import GraphQLConfig, RequestFrontmatter
from drummer.core.storage.project import RequestFile
from drummer.core.variables import resolve
from pathlib import Path

_HTTP_OK = 200


class _MockTransport(httpx.AsyncBaseTransport):
    def __init__(self) -> None:
        self.last_request: httpx.Request | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.last_request = request
        return httpx.Response(
            status_code=_HTTP_OK,
            headers=[("content-type", "application/json")],
            content=b'{"data": {}}',
            request=request,
        )


def _make_request_file(
    graphql: GraphQLConfig | None = None, body: str = ""
) -> RequestFile:
    return RequestFile(
        frontmatter=RequestFrontmatter(
            name="test",
            method="POST",
            url="https://api.example.com/graphql",
            graphql=graphql,
        ),
        body=body,
        path=Path("test.md"),
    )


def test_resolve_passes_graphql_through() -> None:
    gql = GraphQLConfig(query="{ departments { id } }", variables={"limit": 10, "active": True})
    rf = _make_request_file(graphql=gql)
    resolved = resolve(rf, {})
    assert resolved.graphql is not None
    assert resolved.graphql.query == "{ departments { id } }"
    assert resolved.graphql.variables == {"limit": 10, "active": True}


def test_resolve_substitutes_variables_in_query() -> None:
    gql = GraphQLConfig(query="query { {{field}} { id } }", variables={})
    rf = _make_request_file(graphql=gql)
    resolved = resolve(rf, {"field": "departments"})
    assert resolved.graphql is not None
    assert resolved.graphql.query == "query { departments { id } }"


def test_resolve_graphql_none_when_not_set() -> None:
    rf = _make_request_file()
    resolved = resolve(rf, {})
    assert resolved.graphql is None


async def test_engine_synthesizes_graphql_body() -> None:
    gql = GraphQLConfig(query="{ departments { id } }", variables={"limit": 5})
    transport = _MockTransport()
    resolved = ResolvedRequest(
        name="test",
        method="POST",
        url="https://api.example.com/graphql",
        graphql=gql,
    )
    await send(resolved, CookieJar(), transport=transport)
    assert transport.last_request is not None
    body = json.loads(transport.last_request.content)
    assert body["query"] == "{ departments { id } }"
    assert body["variables"] == {"limit": 5}


async def test_engine_injects_content_type_header() -> None:
    gql = GraphQLConfig(query="{ ok }", variables={})
    transport = _MockTransport()
    resolved = ResolvedRequest(
        name="test",
        method="POST",
        url="https://api.example.com/graphql",
        graphql=gql,
    )
    await send(resolved, CookieJar(), transport=transport)
    assert transport.last_request is not None
    assert transport.last_request.headers["content-type"] == "application/json"


async def test_engine_does_not_override_existing_content_type() -> None:
    gql = GraphQLConfig(query="{ ok }", variables={})
    transport = _MockTransport()
    resolved = ResolvedRequest(
        name="test",
        method="POST",
        url="https://api.example.com/graphql",
        headers={"Content-Type": "application/json; charset=utf-8"},
        graphql=gql,
    )
    await send(resolved, CookieJar(), transport=transport)
    assert transport.last_request is not None
    assert transport.last_request.headers["content-type"] == "application/json; charset=utf-8"


async def test_engine_ignores_body_when_graphql_set() -> None:
    gql = GraphQLConfig(query="{ ok }", variables={})
    transport = _MockTransport()
    resolved = ResolvedRequest(
        name="test",
        method="POST",
        url="https://api.example.com/graphql",
        body="should be ignored",
        graphql=gql,
    )
    await send(resolved, CookieJar(), transport=transport)
    assert transport.last_request is not None
    raw = transport.last_request.content.decode()
    assert "should be ignored" not in raw
    assert "query" in json.loads(raw)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/curtis/dev/claude_projects/drummer
python -m pytest tests/unit/test_graphql_engine.py -v 2>&1 | head -40
```

Expected: ImportError or AttributeError (GraphQLConfig missing `Any` field, ResolvedRequest missing graphql field).

- [ ] **Step 3: Fix `formats.py` — widen `variables` to `dict[str, Any]`**

In `drummer/core/storage/formats.py`:

Change line 3 from:
```python
from typing import Literal
```
to:
```python
from typing import Any, Literal
```

Change line 40 (the `variables` field of `GraphQLConfig`) from:
```python
    variables: dict[str, str] = Field(default_factory=dict)
```
to:
```python
    variables: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Fix `engine.py` — add `graphql` field and body synthesis**

In `drummer/core/engine.py`:

**a) Add `import json` after line 1 (`import time`):**
```python
import json
import time
```

**b) Add `GraphQLConfig` to the formats import (line 10):**
```python
from drummer.core.storage.formats import CookieConfig, CookieMode, GraphQLConfig, HttpMethod
```

**c) Add `graphql` field to `ResolvedRequest` after `variables` (around line 26):**
```python
    variables: dict[str, str] = Field(default_factory=dict)
    graphql: GraphQLConfig | None = None
```

**d) Replace the `content = ...` line (line 97) with GraphQL-aware synthesis:**

Current:
```python
    content = encode_body(send_body, resolved.encoding) if send_body else None
```

Replace with:
```python
    if resolved.graphql is not None:
        graphql_body = json.dumps(
            {"query": resolved.graphql.query, "variables": resolved.graphql.variables}
        )
        content = encode_body(graphql_body, resolved.encoding)
        if not any(k.lower() == "content-type" for k in send_headers):
            send_headers["Content-Type"] = "application/json"
    else:
        content = encode_body(send_body, resolved.encoding) if send_body else None
```

- [ ] **Step 5: Fix `variables.py` — pass graphql through `resolve()`**

In `drummer/core/variables.py`:

**a) Add `GraphQLConfig` to the formats import (line 5):**
```python
from drummer.core.storage.formats import AuthType, GraphQLConfig, RequestFile
```

**b) In the `resolve()` function, add graphql resolution before the `return` statement:**

Add after the `effective_timeout = ...` line and before `return ResolvedRequest(...)`:
```python
    graphql_resolved: GraphQLConfig | None = None
    if fm.graphql is not None:
        graphql_resolved = GraphQLConfig(
            query=sub(fm.graphql.query),
            variables=fm.graphql.variables,
        )
```

**c) Add `graphql=graphql_resolved` to the `return ResolvedRequest(...)` call:**
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
        warnings=sorted(seen),
        pre_script=fm.pre_script,
        post_script=fm.post_script,
        script_timeout_ms=effective_timeout,
        variables=dict(env),
        graphql=graphql_resolved,
    )
```

- [ ] **Step 6: Run unit tests and confirm they pass**

```bash
python -m pytest tests/unit/test_graphql_engine.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 7: Run `make check` to confirm no regressions**

```bash
make check
```

Expected: all unit + integration tests pass, ruff + pyright clean.

- [ ] **Step 8: Commit**

```bash
git add drummer/core/storage/formats.py drummer/core/engine.py drummer/core/variables.py tests/unit/test_graphql_engine.py
git commit -m "feat: add GraphQL data model and send pipeline synthesis"
```

---

## Task 2: Introspection endpoint

**Files:**
- Create: `drummer/api/routes/graphql_routes.py`
- Modify: `drummer/api/app.py`
- Create: `tests/unit/test_graphql_introspect.py`
- Create: `tests/integration/test_graphql_introspect.py`
- Create: `tests/integration/test_graphql_send.py`

---

- [ ] **Step 1: Write the failing unit tests**

Create `tests/unit/test_graphql_introspect.py`:

```python
import pytest
from pydantic import ValidationError

from drummer.api.routes.graphql_routes import IntrospectRequest


def test_introspect_request_requires_url() -> None:
    with pytest.raises(ValidationError):
        IntrospectRequest.model_validate({})


def test_introspect_request_accepts_optional_headers() -> None:
    req = IntrospectRequest.model_validate({"url": "https://api.example.com/graphql"})
    assert req.headers == {}


def test_introspect_request_stores_provided_headers() -> None:
    req = IntrospectRequest.model_validate(
        {"url": "https://api.example.com/graphql", "headers": {"Authorization": "Bearer tok"}}
    )
    assert req.headers["Authorization"] == "Bearer tok"
```

- [ ] **Step 2: Run unit tests to confirm they fail**

```bash
python -m pytest tests/unit/test_graphql_introspect.py -v 2>&1 | head -20
```

Expected: ModuleNotFoundError for `graphql_routes`.

- [ ] **Step 3: Create `drummer/api/routes/graphql_routes.py`**

```python
import json
from http import HTTPStatus

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter()

_INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types { ...FullType }
    directives {
      name
      description
      locations
      args { ...InputValue }
    }
  }
}
fragment FullType on __Type {
  kind
  name
  description
  fields(includeDeprecated: true) {
    name
    description
    args { ...InputValue }
    type { ...TypeRef }
    isDeprecated
    deprecationReason
  }
  inputFields { ...InputValue }
  interfaces { ...TypeRef }
  enumValues(includeDeprecated: true) {
    name
    description
    isDeprecated
    deprecationReason
  }
  possibleTypes { ...TypeRef }
}
fragment InputValue on __InputValue {
  name
  description
  type { ...TypeRef }
  defaultValue
}
fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType { kind name ofType { kind name ofType { kind name } } }
        }
      }
    }
  }
}
"""


class IntrospectRequest(BaseModel):
    url: str
    headers: dict[str, str] = Field(default_factory=dict)


@router.post("/graphql/introspect")
async def introspect(body: IntrospectRequest, request: Request) -> JSONResponse:
    transport: httpx.AsyncBaseTransport | None = request.app.state.transport
    payload = json.dumps({"query": _INTROSPECTION_QUERY}).encode()
    headers = {"Content-Type": "application/json", **body.headers}
    try:
        async with httpx.AsyncClient(transport=transport) as client:
            upstream = await client.post(body.url, content=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_GATEWAY, detail=str(exc)
        ) from exc
    if not upstream.is_success:
        raise HTTPException(
            status_code=HTTPStatus.BAD_GATEWAY, detail=upstream.text
        )
    return JSONResponse(content=upstream.json())
```

- [ ] **Step 4: Mount the router in `app.py`**

In `drummer/api/app.py`:

**a) Add the import alphabetically between `environments` and `history`:**
```python
from drummer.api.routes import graphql_routes
```

The import block should read:
```python
from drummer.api.routes import cookies as cookie_routes
from drummer.api.routes import environments as env_routes
from drummer.api.routes import graphql_routes
from drummer.api.routes import history as history_routes
from drummer.api.routes import mock as mock_routes
from drummer.api.routes import project as project_routes
from drummer.api.routes import requests as req_routes
from drummer.api.routes import send as send_routes
from drummer.api.routes import tutorial as tutorial_routes
```

**b) Add router mount after `env_routes` (alphabetical order):**
```python
    app.include_router(project_routes.router, prefix="/api")
    app.include_router(req_routes.router, prefix="/api")
    app.include_router(env_routes.router, prefix="/api")
    app.include_router(graphql_routes.router, prefix="/api")
    app.include_router(send_routes.router, prefix="/api")
    app.include_router(history_routes.router, prefix="/api")
    app.include_router(cookie_routes.router, prefix="/api")
    app.include_router(mock_routes.router)
    app.include_router(tutorial_routes.router)
```

- [ ] **Step 5: Run unit tests and confirm they pass**

```bash
python -m pytest tests/unit/test_graphql_introspect.py -v
```

Expected: 3 tests pass.

- [ ] **Step 6: Write integration tests for the introspect route**

Create `tests/integration/test_graphql_introspect.py`:

```python
import json
from http import HTTPStatus
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.api.db.session import init_db
from tests.integration.conftest import MockTransport

_FAKE_INTROSPECTION = {
    "data": {
        "__schema": {
            "queryType": {"name": "Query"},
            "mutationType": None,
            "subscriptionType": None,
            "types": [
                {
                    "kind": "OBJECT",
                    "name": "Query",
                    "description": None,
                    "fields": [],
                    "inputFields": None,
                    "interfaces": [],
                    "enumValues": None,
                    "possibleTypes": None,
                }
            ],
            "directives": [],
        }
    }
}


def _make_introspect_app(
    tmp_path: Path,
    mock_status: int = HTTPStatus.OK,
    mock_content: bytes | None = None,
) -> object:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    app = create_app(db_url=db_url)
    content = (
        mock_content
        if mock_content is not None
        else json.dumps(_FAKE_INTROSPECTION).encode()
    )
    app.state.transport = MockTransport(
        status_code=mock_status,
        headers=[("content-type", "application/json")],
        content=content,
    )
    return app


async def test_introspect_success_returns_schema(tmp_path: Path) -> None:
    app = _make_introspect_app(tmp_path)
    await init_db(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/graphql/introspect",
            json={"url": "https://api.example.com/graphql"},
        )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "data" in data
    assert "__schema" in data["data"]


async def test_introspect_upstream_400_returns_502(tmp_path: Path) -> None:
    app = _make_introspect_app(
        tmp_path, mock_status=HTTPStatus.BAD_REQUEST, mock_content=b"Bad Request"
    )
    await init_db(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/graphql/introspect",
            json={"url": "https://api.example.com/graphql"},
        )
    assert response.status_code == HTTPStatus.BAD_GATEWAY
```

- [ ] **Step 7: Write send pipeline integration tests**

Create `tests/integration/test_graphql_send.py`:

```python
import json
from http import HTTPStatus
from pathlib import Path

import httpx
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.api.db.session import init_db
from tests.integration.conftest import parse_sse

_HTTP_OK = 200

_GRAPHQL_MD = """\
---
name: Get Departments
method: POST
url: https://api.example.com/graphql
graphql:
  query: |
    query GetDepts($limit: Int) {
      departments(limit: $limit) { id displayName }
    }
  variables:
    limit: 10
    active: true
---
"""


class _CapturingTransport(httpx.AsyncBaseTransport):
    def __init__(self) -> None:
        self.last_request: httpx.Request | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.last_request = request
        return httpx.Response(
            status_code=_HTTP_OK,
            headers=[("content-type", "application/json")],
            content=b'{"data": {"departments": []}}',
            request=request,
        )


def _make_app(project_dir: Path, transport: httpx.AsyncBaseTransport) -> object:
    db_url = f"sqlite+aiosqlite:///{project_dir / 'test.db'}"
    app = create_app(project_dir=project_dir, db_url=db_url)
    app.state.transport = transport
    return app


async def test_graphql_send_synthesizes_json_body(project_dir: Path) -> None:
    (project_dir / "gql.md").write_text(_GRAPHQL_MD, encoding="utf-8")
    transport = _CapturingTransport()
    app = _make_app(project_dir, transport)
    await init_db(f"sqlite+aiosqlite:///{project_dir / 'test.db'}")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/send", json={"path": "gql.md"})
    assert response.status_code == HTTPStatus.OK
    events = parse_sse(response.text)
    assert any(e["event"] == "status" for e in events)
    assert transport.last_request is not None
    body = json.loads(transport.last_request.content)
    assert "query" in body
    assert "variables" in body


async def test_graphql_send_preserves_typed_variables(project_dir: Path) -> None:
    (project_dir / "gql.md").write_text(_GRAPHQL_MD, encoding="utf-8")
    transport = _CapturingTransport()
    app = _make_app(project_dir, transport)
    await init_db(f"sqlite+aiosqlite:///{project_dir / 'test.db'}")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        await ac.post("/api/send", json={"path": "gql.md"})
    assert transport.last_request is not None
    body = json.loads(transport.last_request.content)
    assert body["variables"]["limit"] == 10
    assert body["variables"]["active"] is True


async def test_graphql_send_sets_content_type(project_dir: Path) -> None:
    (project_dir / "gql.md").write_text(_GRAPHQL_MD, encoding="utf-8")
    transport = _CapturingTransport()
    app = _make_app(project_dir, transport)
    await init_db(f"sqlite+aiosqlite:///{project_dir / 'test.db'}")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        await ac.post("/api/send", json={"path": "gql.md"})
    assert transport.last_request is not None
    assert transport.last_request.headers["content-type"] == "application/json"
```

- [ ] **Step 8: Run all new integration tests**

```bash
python -m pytest tests/integration/test_graphql_introspect.py tests/integration/test_graphql_send.py -v
```

Expected: 5 tests pass.

- [ ] **Step 9: Run `make check`**

```bash
make check
```

Expected: all tests pass, ruff + pyright clean.

- [ ] **Step 10: Commit**

```bash
git add drummer/api/routes/graphql_routes.py drummer/api/app.py \
        tests/unit/test_graphql_introspect.py \
        tests/integration/test_graphql_introspect.py \
        tests/integration/test_graphql_send.py
git commit -m "feat: add GraphQL introspection proxy endpoint and integration tests"
```

---

## Task 3: Frontend types + npm deps

**Files:**
- Modify: `frontend/src/types.ts`
- Run: `npm install` in `frontend/`

---

- [ ] **Step 1: Add `GraphQLConfig` to `types.ts`**

In `frontend/src/types.ts`:

**a) Add the `GraphQLConfig` interface after `AuthConfig`:**
```typescript
export interface GraphQLConfig {
  query: string;
  variables: Record<string, unknown>;
}
```

**b) Add `graphql?: GraphQLConfig` to `RequestFrontmatter`:**
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
  graphql?: GraphQLConfig;
  pre_script: string;
  post_script: string;
  script_timeout_ms: number | null;
  tags: string[];
  skip: boolean;
}
```

- [ ] **Step 2: Install `cm6-graphql` (and make `graphql` an explicit dep)**

```bash
cd /Users/curtis/dev/claude_projects/drummer/frontend && npm install graphql cm6-graphql
```

Expected: both packages added to `package.json` `dependencies`.

- [ ] **Step 3: Verify TypeScript types for `cm6-graphql`**

```bash
cat node_modules/cm6-graphql/dist/index.d.ts 2>/dev/null || cat node_modules/cm6-graphql/index.d.ts 2>/dev/null | head -20
```

Confirm the export name (expected: `graphqlExtension(schema?: GraphQLSchema): Extension`). Note the exact name — the code in Task 4 uses `graphqlExtension`.

- [ ] **Step 4: Run the frontend type-check**

```bash
cd /Users/curtis/dev/claude_projects/drummer/frontend && npm run typecheck 2>&1 | head -30
```

Expected: zero new errors (existing errors, if any, are pre-existing).

- [ ] **Step 5: Commit**

```bash
cd /Users/curtis/dev/claude_projects/drummer
git add frontend/src/types.ts frontend/package.json frontend/package-lock.json
git commit -m "feat: add GraphQLConfig frontend type and install cm6-graphql"
```

---

## Task 4: GraphQL components

**Files:**
- Create: `frontend/src/components/request/SchemaExplorer.tsx`
- Create: `frontend/src/components/request/GraphQLTab.tsx`

---

- [ ] **Step 1: Create `SchemaExplorer.tsx`**

Create `frontend/src/components/request/SchemaExplorer.tsx`:

```tsx
import { useState } from "react";
import {
  isEnumType,
  isInputObjectType,
  isInterfaceType,
  isIntrospectionType,
  isObjectType,
  isScalarType,
  isUnionType,
  type GraphQLNamedType,
  type GraphQLSchema,
} from "graphql";

interface Props {
  schema: GraphQLSchema | null;
  onFetch: () => void;
  fetching: boolean;
}

function typeKindLabel(type: GraphQLNamedType): string {
  if (isObjectType(type)) return "object";
  if (isScalarType(type)) return "scalar";
  if (isInputObjectType(type)) return "input";
  if (isEnumType(type)) return "enum";
  if (isInterfaceType(type)) return "interface";
  if (isUnionType(type)) return "union";
  return "";
}

function typeFields(type: GraphQLNamedType): { name: string; typeStr: string }[] {
  if (isObjectType(type) || isInterfaceType(type) || isInputObjectType(type)) {
    return Object.values(type.getFields()).map((f) => ({
      name: f.name,
      typeStr: f.type.toString(),
    }));
  }
  return [];
}

function TypeRow({
  type,
  defaultExpanded,
}: {
  type: GraphQLNamedType;
  defaultExpanded: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const fields = typeFields(type);
  const hasFields = fields.length > 0;

  return (
    <div>
      <button
        type="button"
        onClick={() => hasFields && setExpanded((e) => !e)}
        className={`flex w-full items-center gap-1 px-2 py-0.5 text-left text-xs ${
          hasFields ? "cursor-pointer hover:bg-gray-100" : "cursor-default"
        }`}
      >
        <span className="w-3 text-purple-400">
          {hasFields ? (expanded ? "▼" : "▶") : ""}
        </span>
        <span className="font-medium text-purple-700">{type.name}</span>
        <span className="ml-1 text-[10px] text-gray-400">{typeKindLabel(type)}</span>
      </button>
      {expanded && hasFields && (
        <div className="py-0.5 pl-6">
          {fields.map((f) => (
            <div key={f.name} className="py-0.5 text-xs">
              <span className="text-blue-600">{f.name}</span>
              <span className="text-gray-400"> {f.typeStr}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FetchButton({
  fetching,
  onFetch,
}: {
  fetching: boolean;
  onFetch: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onFetch}
      disabled={fetching}
      className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700 hover:bg-gray-200 disabled:opacity-50"
    >
      {fetching ? "Fetching…" : "Fetch Schema"}
    </button>
  );
}

export function SchemaExplorer({ schema, onFetch, fetching }: Props) {
  if (!schema) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-gray-400">
        <p className="text-sm">No schema loaded</p>
        <FetchButton fetching={fetching} onFetch={onFetch} />
      </div>
    );
  }

  const typeMap = schema.getTypeMap();
  const queryType = schema.getQueryType();
  const mutationType = schema.getMutationType();
  const subscriptionType = schema.getSubscriptionType();
  const rootNames = new Set(
    [queryType?.name, mutationType?.name, subscriptionType?.name].filter(
      (n): n is string => n != null,
    ),
  );
  const rootTypes = [queryType, mutationType, subscriptionType].filter(
    (t): t is NonNullable<typeof t> => t != null,
  );
  const objectTypes = Object.values(typeMap).filter(
    (t) => isObjectType(t) && !rootNames.has(t.name) && !isIntrospectionType(t),
  );
  const otherTypes = Object.values(typeMap).filter(
    (t) => !isObjectType(t) && !isIntrospectionType(t),
  );
  const builtinTypes = Object.values(typeMap).filter(isIntrospectionType);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b px-2 py-1">
        <span className="text-xs text-gray-500">Schema</span>
        <FetchButton fetching={fetching} onFetch={onFetch} />
      </div>
      <div className="flex-1 overflow-auto py-1">
        {rootTypes.length > 0 && (
          <>
            <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
              Root Types
            </div>
            {rootTypes.map((t) => (
              <TypeRow key={t.name} type={t} defaultExpanded />
            ))}
          </>
        )}
        {objectTypes.length > 0 && (
          <>
            <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
              Object Types
            </div>
            {objectTypes.map((t) => (
              <TypeRow key={t.name} type={t} defaultExpanded />
            ))}
          </>
        )}
        {otherTypes.length > 0 && (
          <>
            <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
              Other Types
            </div>
            {otherTypes.map((t) => (
              <TypeRow key={t.name} type={t} defaultExpanded={false} />
            ))}
          </>
        )}
        {builtinTypes.length > 0 && (
          <>
            <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
              Built-in
            </div>
            {builtinTypes.map((t) => (
              <TypeRow key={t.name} type={t} defaultExpanded={false} />
            ))}
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `GraphQLTab.tsx`**

Create `frontend/src/components/request/GraphQLTab.tsx`.

Note: verify the `cm6-graphql` export name in `node_modules/cm6-graphql/dist/index.d.ts` before copy-pasting. The code below uses `graphqlExtension` — adjust if the package uses a different name.

```tsx
import { json as jsonLang } from "@codemirror/lang-json";
import { Compartment, EditorState } from "@codemirror/state";
import { basicSetup, EditorView } from "codemirror";
import {
  buildClientSchema,
  type GraphQLSchema,
  type IntrospectionQuery,
} from "graphql";
import { graphqlExtension } from "cm6-graphql";
import { useEffect, useRef, useState } from "react";
import { useRequestStore } from "../../store/requestStore";
import type { GraphQLConfig } from "../../types";
import { SchemaExplorer } from "./SchemaExplorer";

type GqlTab = "query" | "variables" | "schema";

function QueryEditor({ schema }: { schema: GraphQLSchema | null }) {
  const { draft, saved, patch } = useRequestStore();
  const current = draft ?? saved;
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const patchRef = useRef(patch);
  const graphqlRef = useRef<GraphQLConfig>(
    current?.frontmatter.graphql ?? { query: "", variables: {} },
  );
  const schemaCompartment = useRef(new Compartment());

  useEffect(() => {
    patchRef.current = patch;
  }, [patch]);

  useEffect(() => {
    graphqlRef.current =
      current?.frontmatter.graphql ?? { query: "", variables: {} };
  }, [current]);

  useEffect(() => {
    if (!editorRef.current) return;
    const view = new EditorView({
      state: EditorState.create({
        doc: graphqlRef.current.query,
        extensions: [
          basicSetup,
          schemaCompartment.current.of(
            graphqlExtension(schema ?? undefined),
          ),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              const q = update.state.doc.toString();
              patchRef.current({ graphql: { ...graphqlRef.current, query: q } });
            }
          }),
        ],
      }),
      parent: editorRef.current,
    });
    viewRef.current = view;
    return () => view.destroy();
  }, []); // One-time init — uses patchRef and graphqlRef to avoid stale closures

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    view.dispatch({
      effects: schemaCompartment.current.reconfigure(
        graphqlExtension(schema ?? undefined),
      ),
    });
  }, [schema]);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const stored = current?.frontmatter.graphql?.query ?? "";
    const cur = view.state.doc.toString();
    if (cur !== stored) {
      view.dispatch({ changes: { from: 0, to: cur.length, insert: stored } });
    }
  }, [current]);

  return <div ref={editorRef} className="flex-1 overflow-auto text-sm" />;
}

function VariablesEditor() {
  const { draft, saved, patch } = useRequestStore();
  const current = draft ?? saved;
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const patchRef = useRef(patch);
  const graphqlRef = useRef<GraphQLConfig>(
    current?.frontmatter.graphql ?? { query: "", variables: {} },
  );

  useEffect(() => {
    patchRef.current = patch;
  }, [patch]);

  useEffect(() => {
    graphqlRef.current =
      current?.frontmatter.graphql ?? { query: "", variables: {} };
  }, [current]);

  useEffect(() => {
    if (!editorRef.current) return;
    const view = new EditorView({
      state: EditorState.create({
        doc: JSON.stringify(graphqlRef.current.variables, null, 2),
        extensions: [
          basicSetup,
          jsonLang(),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              const text = update.state.doc.toString();
              try {
                const vars = JSON.parse(text) as Record<string, unknown>;
                patchRef.current({
                  graphql: { ...graphqlRef.current, variables: vars },
                });
              } catch {
                // Skip patch while JSON is invalid mid-edit
              }
            }
          }),
        ],
      }),
      parent: editorRef.current,
    });
    viewRef.current = view;
    return () => view.destroy();
  }, []); // One-time init — uses patchRef and graphqlRef to avoid stale closures

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const stored = JSON.stringify(
      current?.frontmatter.graphql?.variables ?? {},
      null,
      2,
    );
    const cur = view.state.doc.toString();
    if (cur !== stored) {
      view.dispatch({ changes: { from: 0, to: cur.length, insert: stored } });
    }
  }, [current]);

  return <div ref={editorRef} className="flex-1 overflow-auto text-sm" />;
}

export function GraphQLTab() {
  const { draft, saved } = useRequestStore();
  const current = draft ?? saved;
  const [activeTab, setActiveTab] = useState<GqlTab>("query");
  const [schema, setSchema] = useState<GraphQLSchema | null>(null);
  const [fetching, setFetching] = useState(false);

  const handleFetchSchema = async () => {
    if (!current?.frontmatter.url) return;
    setFetching(true);
    try {
      const res = await fetch("/api/graphql/introspect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: current.frontmatter.url,
          headers: current.frontmatter.headers,
        }),
      });
      if (res.ok) {
        const data = (await res.json()) as { data: IntrospectionQuery };
        setSchema(buildClientSchema(data.data));
      }
    } catch {
      // Fetch failure leaves schema as null — user can retry
    } finally {
      setFetching(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-1 border-b px-2 py-1">
        {(["query", "variables", "schema"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setActiveTab(t)}
            className={`rounded px-2 py-0.5 text-xs capitalize ${
              activeTab === t
                ? "bg-purple-100 text-purple-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {activeTab === "query" && <QueryEditor schema={schema} />}
      {activeTab === "variables" && <VariablesEditor />}
      {activeTab === "schema" && (
        <SchemaExplorer
          schema={schema}
          onFetch={handleFetchSchema}
          fetching={fetching}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Run the frontend type-check**

```bash
cd /Users/curtis/dev/claude_projects/drummer/frontend && npm run typecheck 2>&1 | head -40
```

Expected: zero errors. If `cm6-graphql` has a different export name than `graphqlExtension`, fix the import in `GraphQLTab.tsx`.

- [ ] **Step 4: Run biome lint**

```bash
cd /Users/curtis/dev/claude_projects/drummer/frontend && npm run check 2>&1 | head -40
```

Fix any issues (no suppression comments — fix root causes). Common issues:
- `useExhaustiveDependencies`: if biome flags the one-time init effects, add a comment explaining the intentional empty dep array (biome allows `// One-time init` explanatory comments that are not disable comments)
- `noExplicitAny`: ensure no `any` in the code

- [ ] **Step 5: Commit**

```bash
cd /Users/curtis/dev/claude_projects/drummer
git add frontend/src/components/request/SchemaExplorer.tsx \
        frontend/src/components/request/GraphQLTab.tsx
git commit -m "feat: add SchemaExplorer and GraphQLTab components"
```

---

## Task 5: BodyTab wiring + full check

**Files:**
- Modify: `frontend/src/components/request/BodyTab.tsx`

---

- [ ] **Step 1: Rewrite `BodyTab.tsx` with GraphQL wiring**

Replace `frontend/src/components/request/BodyTab.tsx` with:

```tsx
import { EditorState } from "@codemirror/state";
import { basicSetup, EditorView } from "codemirror";
import { useEffect, useRef, useState } from "react";
import { useRequestStore } from "../../store/requestStore";
import type { BodyMode } from "../../types";
import { GraphQLTab } from "./GraphQLTab";

export function BodyTab() {
  const { saved, draft, patch } = useRequestStore();
  const current = draft ?? saved;
  const body = current?.body ?? "";
  const [mode, setMode] = useState<BodyMode>("raw");

  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const patchRef = useRef(patch);

  useEffect(() => {
    patchRef.current = patch;
  }, [patch]);

  // Sync mode when request changes (path changes) or graphql presence changes
  const path = current?.path;
  const hasGraphql = current?.frontmatter.graphql != null;
  useEffect(() => {
    setMode(hasGraphql ? "graphql" : "raw");
  }, [path, hasGraphql]);

  // Initialize CodeMirror once — editor div is always mounted (hidden when inactive)
  useEffect(() => {
    if (!editorRef.current) return;
    const view = new EditorView({
      state: EditorState.create({
        doc: "",
        extensions: [
          basicSetup,
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              patchRef.current({ body: update.state.doc.toString() });
            }
          }),
        ],
      }),
      parent: editorRef.current,
    });
    viewRef.current = view;
    return () => view.destroy();
  }, []); // One-time init — uses patchRef to avoid stale closure

  // Sync body prop to editor
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const cur = view.state.doc.toString();
    if (cur !== body) {
      view.dispatch({ changes: { from: 0, to: cur.length, insert: body } });
    }
  }, [body]);

  const handleModeChange = (newMode: BodyMode) => {
    if (newMode === "graphql" && !current?.frontmatter.graphql) {
      patch({ graphql: { query: "", variables: {} }, method: "POST" });
    }
    setMode(newMode);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-1 border-b px-2 py-1">
        {(["raw", "json", "form-data", "graphql"] as BodyMode[]).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => handleModeChange(m)}
            className={`rounded px-2 py-0.5 text-xs capitalize ${
              mode === m
                ? "bg-purple-100 text-purple-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {m === "form-data"
              ? "Form Data"
              : m.charAt(0).toUpperCase() + m.slice(1)}
          </button>
        ))}
      </div>
      {mode === "form-data" && (
        <p className="p-4 text-sm text-gray-400">Form-data editor coming soon.</p>
      )}
      {mode === "graphql" && <GraphQLTab />}
      {/* Editor div stays mounted; hidden when inactive to preserve CodeMirror state */}
      <div
        ref={editorRef}
        className={`flex-1 overflow-auto text-sm ${
          mode === "raw" || mode === "json" ? "" : "hidden"
        }`}
      />
    </div>
  );
}
```

- [ ] **Step 2: Run frontend type-check**

```bash
cd /Users/curtis/dev/claude_projects/drummer/frontend && npm run typecheck 2>&1 | head -30
```

Expected: zero errors. If `BodyMode` is not exported from `types.ts` for import (it's a type alias defined in both files), remove the import and redefine locally as `type BodyMode = "raw" | "json" | "form-data" | "graphql"`.

- [ ] **Step 3: Run biome**

```bash
cd /Users/curtis/dev/claude_projects/drummer/frontend && npm run check 2>&1 | head -40
```

Fix any issues without suppression comments.

- [ ] **Step 4: Run `make check` (full backend + frontend check)**

```bash
cd /Users/curtis/dev/claude_projects/drummer && make check
```

Expected: all tests pass, ruff + pyright + pytest clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/request/BodyTab.tsx
git commit -m "feat: wire GraphQLTab into BodyTab — Phase 8 complete"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Task |
|------------------|------|
| `GraphQLConfig.variables: dict[str, Any]` | Task 1 |
| `ResolvedRequest.graphql` field | Task 1 |
| Variable substitution in `graphql.query` | Task 1 |
| Body synthesis: `{"query":..., "variables":...}` | Task 1 |
| Content-Type injection, no override | Task 1 |
| `body` field ignored when graphql set | Task 1 |
| `POST /api/graphql/introspect` route | Task 2 |
| httpx transport injection for tests | Task 2 |
| 502 on upstream error | Task 2 |
| `GraphQLConfig` TS type + `graphql?` on `RequestFrontmatter` | Task 3 |
| `cm6-graphql` installed | Task 3 |
| `SchemaExplorer` with type explorer tree | Task 4 |
| Root / Object / Other / Built-in grouping | Task 4 |
| Fetch Schema button + spinner | Task 4 |
| `GraphQLTab` with three sub-tabs | Task 4 |
| CodeMirror query editor with `cm6-graphql` + Compartment | Task 4 |
| CodeMirror variables editor with JSON mode | Task 4 |
| Schema fetch via `/api/graphql/introspect` | Task 4 |
| `buildClientSchema` for autocomplete | Task 4 |
| Enable graphql button in BodyTab | Task 5 |
| Mode init from `frontmatter.graphql` on load | Task 5 |
| `patch({ graphql: {...}, method: "POST" })` on first switch | Task 5 |
| Render `<GraphQLTab />` when mode === "graphql" | Task 5 |

All spec requirements are covered. No placeholders.
