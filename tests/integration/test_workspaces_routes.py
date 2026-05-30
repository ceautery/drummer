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


async def test_list_returns_scratch_active(client: AsyncClient) -> None:
    r = await client.get("/api/workspaces")
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert data["active"] == "scratch"
    assert data["workspaces"][0]["is_scratch"] is True


async def test_create_workspace(client: AsyncClient) -> None:
    r = await client.post("/api/workspaces", json={"name": "My API"})
    assert r.status_code == HTTPStatus.OK
    assert r.json()["id"] == "my-api"


async def test_create_duplicate_conflicts(client: AsyncClient) -> None:
    await client.post("/api/workspaces", json={"name": "My API"})
    r = await client.post("/api/workspaces", json={"name": "my api"})
    assert r.status_code == HTTPStatus.CONFLICT


async def test_switch_active(client: AsyncClient) -> None:
    await client.post("/api/workspaces", json={"name": "My API"})
    r = await client.post("/api/workspaces/active", json={"id": "my-api"})
    assert r.status_code == HTTPStatus.OK
    assert r.json()["id"] == "my-api"
    assert (await client.get("/api/workspaces")).json()["active"] == "my-api"


async def test_switch_unknown_404(client: AsyncClient) -> None:
    r = await client.post("/api/workspaces/active", json={"id": "ghost"})
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_register_external(client: AsyncClient, tmp_path: Path) -> None:
    external = tmp_path / "ext-repo"
    external.mkdir()
    r = await client.post("/api/workspaces/register", json={"path": str(external)})
    assert r.status_code == HTTPStatus.OK
    assert r.json()["kind"] == "external"


async def test_switch_back_to_scratch(client: AsyncClient) -> None:
    await client.post("/api/workspaces", json={"name": "My API"})
    await client.post("/api/workspaces/active", json={"id": "my-api"})
    r = await client.post("/api/workspaces/active", json={"id": "scratch"})
    assert r.status_code == HTTPStatus.OK
    assert r.json()["is_scratch"] is True
    assert (await client.get("/api/workspaces")).json()["active"] == "scratch"


async def test_switch_workspace_changes_request_list(client: AsyncClient) -> None:
    """Switching the active workspace repoints what GET /api/requests returns."""
    # Create the "Other" workspace and write a request file into it.
    await client.post("/api/workspaces", json={"name": "Other"})
    other_dir = ws.resolve_workspace("other")
    request_file = other_dir / "other-request.md"
    request_file.write_text(
        "---\nname: Other Request\nurl: https://other.example.com/data\n---\n", encoding="utf-8"
    )

    # While scratch is active, the "Other" request must not appear.
    r = await client.get("/api/requests")
    assert r.status_code == HTTPStatus.OK
    paths = {item["path"] for item in r.json()}
    assert "other-request.md" not in paths

    # Switch to "other" and confirm the request IS visible.
    switch_r = await client.post("/api/workspaces/active", json={"id": "other"})
    assert switch_r.status_code == HTTPStatus.OK

    r = await client.get("/api/requests")
    assert r.status_code == HTTPStatus.OK
    paths = {item["path"] for item in r.json()}
    assert "other-request.md" in paths


async def test_forget_external_route(client: AsyncClient, tmp_path: Path) -> None:
    external = tmp_path / "ext-to-forget"
    external.mkdir()
    register = await client.post("/api/workspaces/register", json={"path": str(external)})
    assert register.status_code == HTTPStatus.OK
    ext_id = register.json()["id"]

    forget = await client.post("/api/workspaces/forget", json={"id": ext_id})
    assert forget.status_code == HTTPStatus.OK
    body = forget.json()
    assert all(w["id"] != ext_id for w in body["workspaces"])
    assert body["active"] == "scratch"
