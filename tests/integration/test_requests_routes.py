from http import HTTPStatus

from httpx import AsyncClient


async def test_app_boots(client: AsyncClient) -> None:
    response = await client.get("/api/requests")
    assert response.status_code == HTTPStatus.OK
