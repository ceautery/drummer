import json
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, cast

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.api.db.models import ResponseHistoryRecord
from drummer.api.db.session import init_db

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

EXPECTED_RECORD_COUNT = 2


def _db_url(db_path: Path) -> str:
    return f"sqlite+aiosqlite:///{db_path / 'test.db'}"


async def _seed_record(app: FastAPI, i: int = 0) -> str:
    """Insert a history record directly into the db and return its id."""
    record_id = f"test-id-{i}"
    factory = cast("async_sessionmaker[AsyncSession]", app.state.db_factory)
    async with factory() as session:
        record = ResponseHistoryRecord(
            id=record_id,
            sent_at=datetime.now(UTC),
            request_path=f"request-{i}.md",
            request_name=f"Request {i}",
            environment="local",
            method="GET",
            url="https://api.example.com",
            status_code=200,
            elapsed_ms=10.0,
            request_headers=json.dumps([]),
            request_body="",
            response_headers=json.dumps([("content-type", "application/json")]),
            response_body='{"ok": true}',
            encoding="utf-8",
            warnings=json.dumps([]),
        )
        session.add(record)
        await session.commit()
    return record_id


async def test_list_history_empty(client: AsyncClient) -> None:
    response = await client.get("/api/history")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


async def test_list_history_returns_records(project_dir: Path) -> None:
    db_url = _db_url(project_dir)
    application = create_app(project_dir=project_dir, db_url=db_url)
    await init_db(db_url)

    await _seed_record(application, 0)
    await _seed_record(application, 1)

    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
        response = await ac.get("/api/history")
        records = response.json()
        assert len(records) == EXPECTED_RECORD_COUNT
        assert records[0]["id"] in ("test-id-0", "test-id-1")


async def test_list_history_filter_by_path(project_dir: Path) -> None:
    db_url = _db_url(project_dir)
    application = create_app(project_dir=project_dir, db_url=db_url)
    await init_db(db_url)

    await _seed_record(application, 0)
    await _seed_record(application, 1)

    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
        response = await ac.get("/api/history?request_path=request-0.md")
        records = response.json()
        assert len(records) == 1
        assert records[0]["request_path"] == "request-0.md"


async def test_delete_history(project_dir: Path) -> None:
    db_url = _db_url(project_dir)
    application = create_app(project_dir=project_dir, db_url=db_url)
    await init_db(db_url)

    await _seed_record(application, 0)

    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
        del_resp = await ac.delete("/api/history")
        assert del_resp.status_code == HTTPStatus.OK
        assert del_resp.json() == {"status": "cleared"}

        list_resp = await ac.get("/api/history")
        assert list_resp.json() == []
