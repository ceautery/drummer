import json
from http import HTTPStatus
from pathlib import Path

import httpx
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.api.db.session import init_db
from tests.integration.conftest import parse_sse

_HTTP_OK = 200
_EXPECTED_LIMIT = 10

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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/send", json={"path": "gql.md"})
    assert transport.last_request is not None
    body = json.loads(transport.last_request.content)
    assert body["variables"]["limit"] == _EXPECTED_LIMIT
    assert body["variables"]["active"] is True


async def test_graphql_send_sets_content_type(project_dir: Path) -> None:
    (project_dir / "gql.md").write_text(_GRAPHQL_MD, encoding="utf-8")
    transport = _CapturingTransport()
    app = _make_app(project_dir, transport)
    await init_db(f"sqlite+aiosqlite:///{project_dir / 'test.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/send", json={"path": "gql.md"})
    assert transport.last_request is not None
    assert transport.last_request.headers["content-type"] == "application/json"
