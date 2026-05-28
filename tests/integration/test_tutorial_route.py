from http import HTTPStatus
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.api.db.session import init_db
from tests.integration.conftest import parse_sse


def _db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


def _make_tutorial_app(tmp_path: Path) -> object:
    db_url = _db_url(tmp_path)
    app = create_app(db_url=db_url)
    app.state.transport = ASGITransport(app=app)
    return app


@pytest.mark.asyncio
async def test_step_0_welcome_returns_400(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/0/send")
    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
async def test_step_1_departments_streams_done(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/1/send")
    assert response.status_code == HTTPStatus.OK
    events = parse_sse(response.text)
    event_names = [e["event"] for e in events]
    assert "status" in event_names
    assert "body" in event_names
    assert "done" in event_names
    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["script_error"] is None  # type: ignore[index]


@pytest.mark.asyncio
async def test_step_1_returns_departments_body(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/1/send")
    events = parse_sse(response.text)
    status_event = next(e for e in events if e["event"] == "status")
    assert status_event["data"]["status_code"] == HTTPStatus.OK  # type: ignore[index]


@pytest.mark.asyncio
async def test_step_5_pre_script_log_captured(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/5/send")
    assert response.status_code == HTTPStatus.OK
    events = parse_sse(response.text)
    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["script_error"] is None  # type: ignore[index]
    logs = done["data"]["script_logs"]  # type: ignore[index]
    assert any("drummer-tutorial-step-6" in log for log in logs)  # type: ignore[operator]


@pytest.mark.asyncio
async def test_step_6_post_script_logs_title(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/6/send")
    assert response.status_code == HTTPStatus.OK
    events = parse_sse(response.text)
    done = next(e for e in events if e["event"] == "done")
    assert done["data"]["script_error"] is None  # type: ignore[index]
    logs = done["data"]["script_logs"]  # type: ignore[index]
    assert any("Self-Portrait" in log for log in logs)  # type: ignore[operator]


@pytest.mark.asyncio
async def test_step_out_of_range_returns_404(tmp_path: Path) -> None:
    app = _make_tutorial_app(tmp_path)
    await init_db(_db_url(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/tutorial/steps/99/send")
    assert response.status_code == HTTPStatus.NOT_FOUND
