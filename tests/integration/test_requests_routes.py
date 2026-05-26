from http import HTTPStatus
from pathlib import Path

from httpx import AsyncClient


async def test_list_requests_empty(client: AsyncClient) -> None:
    response = await client.get("/api/requests")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


async def test_create_and_get_request(client: AsyncClient, project_dir: Path) -> None:
    payload = {
        "path": "users/list.md",
        "name": "List Users",
        "method": "GET",
        "url": "https://api.example.com/users",
        "headers": {"Accept": "application/json"},
        "body": "fetch all users",
    }
    create_resp = await client.post("/api/requests", json=payload)
    assert create_resp.status_code == HTTPStatus.CREATED
    assert (project_dir / "users" / "list.md").exists()

    get_resp = await client.get("/api/requests/users/list.md")
    assert get_resp.status_code == HTTPStatus.OK
    data = get_resp.json()
    assert data["frontmatter"]["name"] == "List Users"
    assert data["frontmatter"]["method"] == "GET"
    assert data["body"] == "fetch all users"


async def test_update_request(client: AsyncClient) -> None:
    await client.post(
        "/api/requests",
        json={
            "path": "ping.md",
            "name": "Ping",
            "method": "GET",
            "url": "https://x.com",
            "headers": {},
            "body": "",
        },
    )
    update_resp = await client.put(
        "/api/requests/ping.md",
        json={
            "path": "ping.md",
            "name": "Ping Updated",
            "method": "POST",
            "url": "https://x.com/ping",
            "headers": {},
            "body": "body",
        },
    )
    assert update_resp.status_code == HTTPStatus.OK
    get_resp = await client.get("/api/requests/ping.md")
    assert get_resp.json()["frontmatter"]["name"] == "Ping Updated"
    assert get_resp.json()["frontmatter"]["method"] == "POST"


async def test_delete_request(client: AsyncClient, project_dir: Path) -> None:
    await client.post(
        "/api/requests",
        json={
            "path": "temp.md",
            "name": "Temp",
            "method": "GET",
            "url": "https://x.com",
            "headers": {},
            "body": "",
        },
    )
    assert (project_dir / "temp.md").exists()
    del_resp = await client.delete("/api/requests/temp.md")
    assert del_resp.status_code == HTTPStatus.NO_CONTENT
    assert not (project_dir / "temp.md").exists()


async def test_get_missing_request_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/requests/does-not-exist.md")
    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_list_requests_returns_summaries(client: AsyncClient) -> None:
    await client.post(
        "/api/requests",
        json={
            "path": "a.md",
            "name": "A",
            "method": "GET",
            "url": "https://a.com",
            "headers": {},
            "body": "",
        },
    )
    await client.post(
        "/api/requests",
        json={
            "path": "b.md",
            "name": "B",
            "method": "POST",
            "url": "https://b.com",
            "headers": {},
            "body": "",
        },
    )
    response = await client.get("/api/requests")
    items = response.json()
    assert len(items) == len(["a.md", "b.md"])
    paths = {item["path"] for item in items}
    assert "a.md" in paths
    assert "b.md" in paths
