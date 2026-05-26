from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from drummer.api.deps import get_project_dir
from drummer.core.storage.formats import (
    RequestFile,
    RequestFrontmatter,
    parse_request_file,
    write_request_file,
)
from drummer.core.storage.project import list_requests

router = APIRouter()

ProjectDir = Annotated[Path, Depends(get_project_dir)]


class CreateRequestBody(BaseModel):
    path: str
    name: str
    method: str = "GET"
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = ""


class RequestSummary(BaseModel):
    path: str
    name: str
    method: str
    url: str


class RequestDetail(BaseModel):
    path: str
    frontmatter: RequestFrontmatter
    body: str


@router.get("/requests")
async def list_requests_route(project_dir: ProjectDir) -> list[RequestSummary]:
    paths = list_requests(project_dir)
    result: list[RequestSummary] = []
    for p in paths:
        rf = parse_request_file(p)
        result.append(
            RequestSummary(
                path=str(p.relative_to(project_dir)),
                name=rf.frontmatter.name,
                method=rf.frontmatter.method,
                url=rf.frontmatter.url,
            )
        )
    return result


@router.get("/requests/{path:path}")
async def get_request_route(path: str, project_dir: ProjectDir) -> RequestDetail:
    full_path = project_dir / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Request not found: {path}")
    rf = parse_request_file(full_path)
    return RequestDetail(path=path, frontmatter=rf.frontmatter, body=rf.body)


@router.post("/requests", status_code=201)
async def create_request_route(body: CreateRequestBody, project_dir: ProjectDir) -> RequestSummary:
    full_path = project_dir / body.path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    fm = RequestFrontmatter.model_validate(
        {"name": body.name, "method": body.method, "url": body.url, "headers": body.headers}
    )
    write_request_file(RequestFile(frontmatter=fm, body=body.body, path=full_path))
    return RequestSummary(path=body.path, name=body.name, method=body.method, url=body.url)


@router.put("/requests/{path:path}")
async def update_request_route(
    path: str, body: CreateRequestBody, project_dir: ProjectDir
) -> RequestSummary:
    full_path = project_dir / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Request not found: {path}")
    fm = RequestFrontmatter.model_validate(
        {"name": body.name, "method": body.method, "url": body.url, "headers": body.headers}
    )
    write_request_file(RequestFile(frontmatter=fm, body=body.body, path=full_path))
    return RequestSummary(path=path, name=body.name, method=body.method, url=body.url)


@router.delete("/requests/{path:path}", status_code=204)
async def delete_request_route(path: str, project_dir: ProjectDir) -> None:
    full_path = project_dir / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Request not found: {path}")
    full_path.unlink()
