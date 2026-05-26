from http import HTTPStatus
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class ProjectInfo(BaseModel):
    name: str
    path: str


class SetProjectBody(BaseModel):
    path: str


def _resolve_and_validate(raw_path: str) -> Path:
    new_dir = Path(raw_path).expanduser().resolve()
    if not (new_dir / ".drummer" / "project.yaml").exists():
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Not a Drummer project (missing .drummer/project.yaml)",
        )
    return new_dir


@router.get("/project")
async def get_project_route(request: Request) -> ProjectInfo:
    project_dir: Path | None = request.app.state.project_dir
    if project_dir is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="No project loaded")
    return ProjectInfo(name=project_dir.name, path=str(project_dir))


@router.post("/project")
async def set_project_route(body: SetProjectBody, request: Request) -> ProjectInfo:
    new_dir = _resolve_and_validate(body.path)
    request.app.state.project_dir = new_dir
    return ProjectInfo(name=new_dir.name, path=str(new_dir))
