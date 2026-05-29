from collections.abc import AsyncGenerator
from http import HTTPStatus
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.api.db.session import init_db
from drummer.core.storage import workspaces as ws


@pytest_asyncio.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    monkeypatch.setenv("DRUMMER_HOME", str(tmp_path / "home"))
    ws.ensure_scratch()
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    application = create_app(project_dir=ws.active_workspace_dir(), db_url=db_url)
    await init_db(db_url)
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
        yield ac


async def test_get_settings_defaults_to_system(client: AsyncClient) -> None:
    r = await client.get("/api/settings")
    assert r.status_code == HTTPStatus.OK
    assert r.json()["theme"] == "system"


async def test_put_settings_round_trips(client: AsyncClient) -> None:
    r = await client.put("/api/settings", json={"theme": "dark"})
    assert r.status_code == HTTPStatus.OK
    assert r.json()["theme"] == "dark"
    assert (await client.get("/api/settings")).json()["theme"] == "dark"


async def test_put_settings_rejects_invalid_theme(client: AsyncClient) -> None:
    r = await client.put("/api/settings", json={"theme": "neon"})
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
