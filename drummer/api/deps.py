from collections.abc import AsyncGenerator
from http import HTTPStatus
from pathlib import Path
from typing import cast

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drummer.core.cookies import CookieJar


def get_project_dir(request: Request) -> Path:
    project_dir: Path | None = request.app.state.project_dir
    if project_dir is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="No project loaded. POST /api/project to load one.",
        )
    return project_dir


def get_cookie_jar(request: Request) -> CookieJar:
    return cast("CookieJar", request.app.state.cookie_jar)


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    factory = cast("async_sessionmaker[AsyncSession]", request.app.state.db_factory)
    async with factory() as session:
        yield session
