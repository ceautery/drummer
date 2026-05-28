from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drummer.api.db.models import CookieRecord


class CookiePersistence:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def load(self) -> dict[str, dict[str, tuple[str, datetime | None]]]:
        now = datetime.now(UTC)
        result: dict[str, dict[str, tuple[str, datetime | None]]] = {}
        async with self._factory() as session:
            rows = await session.execute(select(CookieRecord))
            for record in rows.scalars():
                if record.expires_at is not None:
                    exp = (
                        record.expires_at
                        if record.expires_at.tzinfo
                        else record.expires_at.replace(tzinfo=UTC)
                    )
                    if exp <= now:
                        continue
                    expires_at: datetime | None = exp
                else:
                    expires_at = None
                if record.hostname not in result:
                    result[record.hostname] = {}
                result[record.hostname][record.name] = (record.value, expires_at)
        return result

    async def save(self, hostname: str, name: str, value: str, expires_at: datetime | None) -> None:
        async with self._factory() as session:
            stmt = (
                sqlite_insert(CookieRecord)
                .values(hostname=hostname, name=name, value=value, expires_at=expires_at)
                .on_conflict_do_update(
                    index_elements=["hostname", "name"],
                    set_={"value": value, "expires_at": expires_at},
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def delete(self, hostname: str, name: str) -> None:
        async with self._factory() as session:
            await session.execute(
                delete(CookieRecord).where(
                    CookieRecord.hostname == hostname, CookieRecord.name == name
                )
            )
            await session.commit()

    async def clear(self) -> None:
        async with self._factory() as session:
            await session.execute(delete(CookieRecord))
            await session.commit()
