from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from drummer.api.deps import get_project_dir
from drummer.core.storage.formats import (
    HttpMethod,
    RequestFile,
    RequestFrontmatter,
    delete_request_file,
    ensure_request_dir,
    parse_request_file,
    write_request_file,
)
from drummer.core.storage.project import list_request_files

router = APIRouter()

ProjectDir = Annotated[Path, Depends(get_project_dir)]


def _safe_request_path(project_dir: Path, path: str) -> Path:
    full_path = (project_dir / path).resolve()
    if not full_path.is_relative_to(project_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid path: outside project directory")
    return full_path


class CreateRequestBody(BaseModel):
    path: str
    name: str
    method: HttpMethod = "GET"
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = ""


class RequestSummary(BaseModel):
    path: str
    name: str
    method: HttpMethod
    url: str


class RequestDetail(BaseModel):
    path: str
    frontmatter: RequestFrontmatter
    body: str


@router.get("/requests")
async def list_requests_route(project_dir: ProjectDir) -> list[RequestSummary]:
    request_files = list_request_files(project_dir)
    return [
        RequestSummary(
            path=str(rf.path.relative_to(project_dir)),
            name=rf.frontmatter.name,
            method=rf.frontmatter.method,
            url=rf.frontmatter.url,
        )
        for rf in request_files
    ]


@router.get("/requests/{path:path}")
async def get_request_route(path: str, project_dir: ProjectDir) -> RequestDetail:
    full_path = _safe_request_path(project_dir, path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Request not found: {path}")
    rf = parse_request_file(full_path)
    return RequestDetail(path=path, frontmatter=rf.frontmatter, body=rf.body)


@router.post("/requests", status_code=201)
async def create_request_route(body: CreateRequestBody, project_dir: ProjectDir) -> RequestSummary:
    full_path = _safe_request_path(project_dir, body.path)
    ensure_request_dir(full_path)
    fm = RequestFrontmatter(name=body.name, method=body.method, url=body.url, headers=body.headers)
    write_request_file(RequestFile(frontmatter=fm, body=body.body, path=full_path))
    return RequestSummary(path=body.path, name=body.name, method=body.method, url=body.url)


@router.put("/requests/{path:path}")
async def update_request_route(
    path: str, body: CreateRequestBody, project_dir: ProjectDir
) -> RequestSummary:
    full_path = _safe_request_path(project_dir, path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Request not found: {path}")
    fm = RequestFrontmatter(name=body.name, method=body.method, url=body.url, headers=body.headers)
    write_request_file(RequestFile(frontmatter=fm, body=body.body, path=full_path))
    return RequestSummary(path=path, name=body.name, method=body.method, url=body.url)


@router.delete("/requests/{path:path}", status_code=204)
async def delete_request_route(path: str, project_dir: ProjectDir) -> None:
    full_path = _safe_request_path(project_dir, path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Request not found: {path}")
    delete_request_file(full_path)
