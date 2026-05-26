from http import HTTPStatus
from pathlib import Path

import httpx
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.api.db.session import init_db
from tests.integration.conftest import MockTransport, parse_sse


def _make_app(
    project_dir: Path,
    transport: httpx.AsyncBaseTransport | None = None,
    status_code: int = 200,
    content: bytes = b'{"ok":true}',
) -> object:
    db_url = f"sqlite+aiosqlite:///{project_dir}/test.db"
    application = create_app(project_dir=project_dir, db_url=db_url)
    if transport is not None:
        application.state.transport = transport
    else:
        application.state.transport = MockTransport(
            status_code=status_code, headers=[("content-type", "application/json")], content=content
        )
    return application


async def _init_db_for(project_dir: Path) -> None:
    db_url = f"sqlite+aiosqlite:///{project_dir}/test.db"
    await init_db(db_url)


async def test_send_success_emits_sse_events(project_dir: Path) -> None:
    (project_dir / "ping.md").write_text(
        "---\nname: Ping\nmethod: GET\nurl: https://api.example.com/ping\n---\n", encoding="utf-8"
    )
    app = _make_app(project_dir)
    await _init_db_for(project_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/send", json={"path": "ping.md"})
    assert response.status_code == HTTPStatus.OK
    events = parse_sse(response.text)
    event_names = [e["event"] for e in events]
    assert "status" in event_names
    assert "headers" in event_names
    assert "body" in event_names
    assert "done" in event_names

    status_event = next(e for e in events if e["event"] == "status")
    assert status_event["data"]["status_code"] == HTTPStatus.OK

    done_event = next(e for e in events if e["event"] == "done")
    assert "history_id" in done_event["data"]


async def test_send_writes_history_record(project_dir: Path) -> None:
    (project_dir / "ping.md").write_text(
        "---\nname: Ping\nmethod: GET\nurl: https://api.example.com/ping\n---\n", encoding="utf-8"
    )
    app = _make_app(project_dir)
    await _init_db_for(project_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/send", json={"path": "ping.md"})
        history = await ac.get("/api/history")
    records = history.json()
    assert len(records) == 1
    assert records[0]["request_name"] == "Ping"
    assert records[0]["status_code"] == HTTPStatus.OK


async def test_send_network_failure_emits_error_event(project_dir: Path) -> None:
    class FailTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, _request: httpx.Request) -> httpx.Response:
            msg = "Connection refused"
            raise httpx.ConnectError(msg)

    (project_dir / "ping.md").write_text(
        "---\nname: Ping\nmethod: GET\nurl: https://api.example.com/ping\n---\n", encoding="utf-8"
    )
    app = _make_app(project_dir, transport=FailTransport())
    await _init_db_for(project_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/send", json={"path": "ping.md"})
    events = parse_sse(response.text)
    assert any(e["event"] == "error" for e in events)
    assert not any(e["event"] == "done" for e in events)


async def test_send_no_history_on_failure(project_dir: Path) -> None:
    class FailTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, _request: httpx.Request) -> httpx.Response:
            msg = "Connection refused"
            raise httpx.ConnectError(msg)

    (project_dir / "ping.md").write_text(
        "---\nname: Ping\nmethod: GET\nurl: https://api.example.com/ping\n---\n", encoding="utf-8"
    )
    app = _make_app(project_dir, transport=FailTransport())
    await _init_db_for(project_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/send", json={"path": "ping.md"})
        history = await ac.get("/api/history")
    assert history.json() == []


async def test_send_with_variable_overrides(project_dir: Path) -> None:
    (project_dir / "ping.md").write_text(
        "---\nname: Ping\nmethod: GET\nurl: '{{base_url}}/ping'\n---\n", encoding="utf-8"
    )
    app = _make_app(project_dir)
    await _init_db_for(project_dir)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/send",
            json={"path": "ping.md", "overrides": {"base_url": "https://api.example.com"}},
        )
    events = parse_sse(response.text)
    status_event = next(e for e in events if e["event"] == "status")
    assert "api.example.com" in status_event["data"]["url"]
