from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from drummer.api.db.models import ResponseHistoryRecord
from drummer.api.deps import get_db

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/history")
async def list_history_route(
    db: DbSession, request_path: str = "", limit: int = 100
) -> list[dict[str, object]]:
    stmt = select(ResponseHistoryRecord).order_by(ResponseHistoryRecord.sent_at.desc()).limit(limit)
    if request_path:
        stmt = stmt.where(ResponseHistoryRecord.request_path == request_path)
    result = await db.execute(stmt)
    return [r.to_dict() for r in result.scalars().all()]


@router.delete("/history")
async def delete_history_route(db: DbSession) -> dict[str, str]:
    await db.execute(delete(ResponseHistoryRecord))
    await db.commit()
    return {"status": "cleared"}
