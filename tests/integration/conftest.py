import json
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from drummer.api.app import create_app
from drummer.api.db.session import init_db
from drummer.core.storage.project import create_project


def _db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


@pytest_asyncio.fixture
async def project_dir(tmp_path: Path) -> Path:
    create_project(tmp_path, "Test Project")
    return tmp_path


@pytest_asyncio.fixture
async def client(project_dir: Path) -> AsyncGenerator[AsyncClient, None]:
    db_url = _db_url(project_dir)
    application = create_app(project_dir=project_dir, db_url=db_url)
    await init_db(db_url)
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
        yield ac


class MockTransport(httpx.AsyncBaseTransport):
    def __init__(
        self,
        status_code: int = 200,
        headers: list[tuple[str, str]] | None = None,
        content: bytes = b"",
    ) -> None:
        self._status_code = status_code
        self._headers = headers or [("content-type", "application/json")]
        self._content = content

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=self._status_code,
            headers=self._headers,
            content=self._content,
            request=request,
        )


@pytest_asyncio.fixture
async def client_with_mock(project_dir: Path) -> AsyncGenerator[AsyncClient, None]:
    db_url = _db_url(project_dir)
    application = create_app(project_dir=project_dir, db_url=db_url)
    await init_db(db_url)
    application.state.transport = MockTransport(
        status_code=200, headers=[("content-type", "application/json")], content=b'{"ok": true}'
    )
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
        yield ac


def parse_sse(text: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    current: dict[str, object] = {}
    for line in text.split("\n"):
        if line.startswith("event:"):
            current["event"] = line[len("event:") :].strip()
        elif line.startswith("data:"):
            current["data"] = json.loads(line[len("data:") :].strip())
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events
