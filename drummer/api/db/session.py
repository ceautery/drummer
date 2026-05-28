from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from drummer.api.db.models import Base

_SQLITE_PREFIX = "sqlite+aiosqlite:///"


def async_session_factory(db_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(db_url)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(db_url: str) -> None:
    if db_url.startswith(_SQLITE_PREFIX):
        Path(db_url[len(_SQLITE_PREFIX) :]).parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA auto_vacuum = FULL"))
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
