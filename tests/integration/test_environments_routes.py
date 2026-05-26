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
