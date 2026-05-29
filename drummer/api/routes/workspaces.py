from http import HTTPStatus
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from drummer.core.storage import workspaces as ws
from drummer.core.storage.project import project_exists

router = APIRouter()


class WorkspaceListResponse(BaseModel):
    workspaces: list[ws.WorkspaceInfo]
    active: str


class SwitchBody(BaseModel):
    id: str


class CreateBody(BaseModel):
    name: str


class RegisterBody(BaseModel):
    path: str


@router.get("/workspaces")
async def list_workspaces_route() -> WorkspaceListResponse:
    return WorkspaceListResponse(workspaces=ws.list_workspaces(), active=ws.get_active())


@router.post("/workspaces")
async def create_workspace_route(body: CreateBody) -> ws.WorkspaceInfo:
    try:
        return ws.create_workspace(body.name)
    except ValueError as exc:
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(exc)) from exc


@router.post("/workspaces/register")
async def register_workspace_route(body: RegisterBody) -> ws.WorkspaceInfo:
    return ws.register_external(Path(body.path))


@router.post("/workspaces/active")
async def switch_workspace_route(body: SwitchBody, request: Request) -> ws.WorkspaceInfo:
    target = ws.resolve_workspace(body.id)
    if not project_exists(target):
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Workspace not found")
    ws.set_active(body.id)
    request.app.state.project_dir = target
    for info in ws.list_workspaces():
        if info.id == body.id:
            return info
    return ws.WorkspaceInfo(
        id=body.id, name=target.name, kind="central", path=str(target), is_scratch=False
    )
