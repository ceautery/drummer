from http import HTTPStatus
from pathlib import Path

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app


@pytest_asyncio.fixture
async def app_no_project() -> FastAPI:
    return create_app(project_dir=None)


@pytest_asyncio.fixture
async def app_with_project(project_dir: Path) -> FastAPI:
    return create_app(project_dir=project_dir)


async def test_get_project_returns_404_when_no_project(app_no_project: FastAPI) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app_no_project), base_url="http://test"
    ) as client:
        r = await client.get("/api/project")
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_get_project_returns_info(app_with_project: FastAPI, project_dir: Path) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app_with_project), base_url="http://test"
    ) as client:
        r = await client.get("/api/project")
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert data["name"] == project_dir.name
    assert data["path"] == str(project_dir)


async def test_post_project_sets_project(app_no_project: FastAPI, project_dir: Path) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app_no_project), base_url="http://test"
    ) as client:
        r = await client.post("/api/project", json={"path": str(project_dir)})
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert data["name"] == project_dir.name


async def test_post_project_rejects_non_drummer_dir(
    app_no_project: FastAPI, tmp_path: Path
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app_no_project), base_url="http://test"
    ) as client:
        r = await client.post("/api/project", json={"path": str(tmp_path)})
    assert r.status_code == HTTPStatus.BAD_REQUEST


async def test_requests_route_returns_400_when_no_project(app_no_project: FastAPI) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app_no_project), base_url="http://test"
    ) as client:
        r = await client.get("/api/requests")
    assert r.status_code == HTTPStatus.BAD_REQUEST
