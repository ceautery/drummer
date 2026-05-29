from fastapi import APIRouter
from pydantic import BaseModel

from drummer.core.storage import workspaces as ws

router = APIRouter()


class Settings(BaseModel):
    theme: ws.ThemePref


@router.get("/settings")
async def get_settings_route() -> Settings:
    return Settings(theme=ws.get_theme())


@router.put("/settings")
async def put_settings_route(body: Settings) -> Settings:
    ws.set_theme(body.theme)
    return Settings(theme=ws.get_theme())
