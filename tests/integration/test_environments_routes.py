from http import HTTPStatus

from httpx import AsyncClient


async def test_list_environments_returns_local(client: AsyncClient) -> None:
    response = await client.get("/api/environments")
    assert response.status_code == HTTPStatus.OK
    envs = response.json()
    assert len(envs) == 1
    assert envs[0]["name"] == "local"


async def test_get_environment(client: AsyncClient) -> None:
    response = await client.get("/api/environments/local")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["name"] == "local"
    assert isinstance(data["variables"], dict)


async def test_update_environment_variables(client: AsyncClient) -> None:
    payload = {
        "name": "local",
        "variables": {"base_url": "https://api.example.com", "retries": "3"},
    }
    put_resp = await client.put("/api/environments/local", json=payload)
    assert put_resp.status_code == HTTPStatus.OK

    get_resp = await client.get("/api/environments/local")
    variables = get_resp.json()["variables"]
    assert variables["base_url"] == "https://api.example.com"
    assert variables["retries"] == "3"


async def test_get_missing_environment_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/environments/staging")
    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_update_missing_environment_returns_404(client: AsyncClient) -> None:
    payload = {"name": "staging", "variables": {"base_url": "https://staging.example.com"}}
    response = await client.put("/api/environments/staging", json=payload)
    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_create_environment(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/environments", json={"name": "staging", "variables": {"base_url": "https://s"}}
    )
    assert resp.status_code == HTTPStatus.CREATED
    assert resp.json() == {"name": "staging", "variables": {"base_url": "https://s"}}
    listed = {e["name"] for e in (await client.get("/api/environments")).json()}
    assert "staging" in listed


async def test_create_environment_duplicate_conflicts(client: AsyncClient) -> None:
    await client.post("/api/environments", json={"name": "staging", "variables": {}})
    resp = await client.post("/api/environments", json={"name": "staging", "variables": {}})
    assert resp.status_code == HTTPStatus.CONFLICT


async def test_create_environment_rejects_blank_name(client: AsyncClient) -> None:
    resp = await client.post("/api/environments", json={"name": "   ", "variables": {}})
    assert resp.status_code == HTTPStatus.BAD_REQUEST


async def test_create_environment_rejects_path_name(client: AsyncClient) -> None:
    resp = await client.post("/api/environments", json={"name": "../escape", "variables": {}})
    assert resp.status_code == HTTPStatus.BAD_REQUEST
