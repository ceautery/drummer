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
    assert response.status_code == httpx.codes.OK
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
    assert len(api_reqs) == 1
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
