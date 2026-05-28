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
    tmp_path: Path, mock_status: int = HTTPStatus.OK, mock_content: bytes | None = None
) -> object:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    app = create_app(db_url=db_url)
    content = mock_content if mock_content is not None else json.dumps(_FAKE_INTROSPECTION).encode()
    app.state.transport = MockTransport(
        status_code=mock_status, headers=[("content-type", "application/json")], content=content
    )
    return app


async def test_introspect_success_returns_schema(tmp_path: Path) -> None:
    app = _make_introspect_app(tmp_path)
    await init_db(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/graphql/introspect", json={"url": "https://api.example.com/graphql"}
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/graphql/introspect", json={"url": "https://api.example.com/graphql"}
        )
    assert response.status_code == HTTPStatus.BAD_GATEWAY
