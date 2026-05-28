from http import HTTPStatus

import pytest
from httpx import AsyncClient

_TOTAL_OBJECTS = 25
_TOTAL_DEPARTMENTS = 5
_DEPT_11_COUNT = 7
_VAN_GOGH_ID = 436532
_SUNFLOWERS_ID = 437112
_UNKNOWN_ID = 99999
_DEPT_11 = 11


@pytest.mark.asyncio
async def test_departments_returns_200(client: AsyncClient) -> None:
    response = await client.get("/mock/met/departments")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "departments" in data
    assert len(data["departments"]) == _TOTAL_DEPARTMENTS


@pytest.mark.asyncio
async def test_departments_has_expected_fields(client: AsyncClient) -> None:
    data = (await client.get("/mock/met/departments")).json()
    for dept in data["departments"]:
        assert "departmentId" in dept
        assert "displayName" in dept


@pytest.mark.asyncio
async def test_objects_returns_all_25(client: AsyncClient) -> None:
    response = await client.get("/mock/met/objects")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["total"] == _TOTAL_OBJECTS
    assert len(data["objectIDs"]) == _TOTAL_OBJECTS


@pytest.mark.asyncio
async def test_objects_filters_by_department(client: AsyncClient) -> None:
    response = await client.get(f"/mock/met/objects?departmentIds={_DEPT_11}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["total"] == _DEPT_11_COUNT
    assert _VAN_GOGH_ID in data["objectIDs"]


@pytest.mark.asyncio
async def test_object_detail_returns_van_gogh(client: AsyncClient) -> None:
    response = await client.get(f"/mock/met/objects/{_VAN_GOGH_ID}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "Self-Portrait with a Straw Hat" in data["title"]
    assert data["artistDisplayName"] == "Vincent van Gogh"


@pytest.mark.asyncio
async def test_object_detail_returns_404_for_unknown(client: AsyncClient) -> None:
    response = await client.get(f"/mock/met/objects/{_UNKNOWN_ID}")
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_search_finds_sunflowers(client: AsyncClient) -> None:
    response = await client.get("/mock/met/search?q=sunflowers")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert _SUNFLOWERS_ID in data["objectIDs"]


@pytest.mark.asyncio
async def test_search_empty_query_returns_all(client: AsyncClient) -> None:
    response = await client.get("/mock/met/search")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["total"] == _TOTAL_OBJECTS
