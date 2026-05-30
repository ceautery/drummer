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


async def test_update_request_full_roundtrip(client: AsyncClient) -> None:
    await client.post(
        "/api/requests",
        json={"path": "ping.md", "name": "Ping", "method": "GET", "url": "https://x.com"},
    )
    update_resp = await client.put(
        "/api/requests/ping.md",
        json={
            "frontmatter": {
                "name": "Ping Updated",
                "method": "POST",
                "url": "https://x.com/ping",
                "headers": {"Accept": "application/json"},
            },
            "body": "payload",
        },
    )
    assert update_resp.status_code == HTTPStatus.OK
    data = update_resp.json()
    # The PUT response must be a full RequestDetail, not a bare summary.
    assert data["frontmatter"]["name"] == "Ping Updated"
    assert data["frontmatter"]["method"] == "POST"
    assert data["body"] == "payload"

    get_resp = await client.get("/api/requests/ping.md")
    assert get_resp.json()["frontmatter"]["url"] == "https://x.com/ping"


async def test_update_request_preserves_auth_params_and_scripts(client: AsyncClient) -> None:
    await client.post(
        "/api/requests",
        json={"path": "secure.md", "name": "Secure", "method": "GET", "url": "https://x.com"},
    )
    rich_frontmatter = {
        "name": "Secure",
        "method": "GET",
        "url": "https://x.com",
        "params": {"q": "search"},
        "auth": {"type": "bearer", "token": "secret-token"},
        "post_script": "dm.log('done')",
    }
    await client.put("/api/requests/secure.md", json={"frontmatter": rich_frontmatter, "body": ""})
    # Save again changing ONLY the url, sending the full frontmatter back.
    changed = {**rich_frontmatter, "url": "https://x.com/v2"}
    await client.put("/api/requests/secure.md", json={"frontmatter": changed, "body": ""})

    fm = (await client.get("/api/requests/secure.md")).json()["frontmatter"]
    assert fm["url"] == "https://x.com/v2"
    assert fm["params"] == {"q": "search"}
    assert fm["auth"]["type"] == "bearer"
    assert fm["auth"]["token"] == "secret-token"
    assert fm["post_script"] == "dm.log('done')"


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
    paths = {item["path"] for item in items}
    assert "a.md" in paths
    assert "b.md" in paths
