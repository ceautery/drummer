from http import HTTPStatus

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRUMMER_HOME", str(tmp_path / "home"))


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
