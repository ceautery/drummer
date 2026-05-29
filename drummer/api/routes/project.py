from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from drummer.core.storage.project import load_project

if TYPE_CHECKING:
    from pathlib import Path

router = APIRouter()


class ProjectInfo(BaseModel):
    name: str
    path: str


@router.get("/project")
async def get_project_route(request: Request) -> ProjectInfo:
    project_dir: Path | None = request.app.state.project_dir
    if project_dir is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="No project loaded")
    meta = load_project(project_dir)
    return ProjectInfo(name=meta.name, path=str(project_dir))
