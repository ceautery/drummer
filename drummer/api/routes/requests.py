from fastapi import APIRouter

router = APIRouter()


@router.get("/requests")
async def list_requests_route() -> list[dict[str, str]]:
    return []
