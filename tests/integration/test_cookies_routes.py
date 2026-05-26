from http import HTTPStatus
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app


async def test_list_cookies_empty(client: AsyncClient) -> None:
    response = await client.get("/api/cookies")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {}


async def test_clear_cookies(project_dir: Path) -> None:
    application = create_app(project_dir=project_dir, db_url="sqlite+aiosqlite:///:memory:")
    # Manually seed the cookie jar
    application.state.cookie_jar.update_from_response(
        "https://api.example.com/login", ["session=abc123"]
    )
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
        list_resp = await ac.get("/api/cookies")
        assert list_resp.json() == {"api.example.com": {"session": "abc123"}}

        del_resp = await ac.delete("/api/cookies")
        assert del_resp.status_code == HTTPStatus.OK

        empty_resp = await ac.get("/api/cookies")
        assert empty_resp.json() == {}
