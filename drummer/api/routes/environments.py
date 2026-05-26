from http import HTTPStatus
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from drummer.api.deps import get_project_dir
from drummer.core.storage.project import (
    Environment,
    list_environments,
    load_environment,
    save_environment,
)

router = APIRouter()

ProjectDir = Annotated[Path, Depends(get_project_dir)]

_ENV_NOT_FOUND = "Environment not found"


class EnvironmentSummary(BaseModel):
    name: str
    variable_count: int


class EnvironmentDetail(BaseModel):
    name: str
    variables: dict[str, str] = Field(default_factory=dict)


def _env_path(project_dir: Path, name: str) -> Path:
    return project_dir / ".drummer" / "environments" / f"{name}.yaml"


@router.get("/environments")
async def list_environments_route(project_dir: ProjectDir) -> list[EnvironmentSummary]:
    return [
        EnvironmentSummary(name=env.name, variable_count=len(env.variables))
        for env in list_environments(project_dir)
    ]


@router.get("/environments/{name}")
async def get_environment_route(name: str, project_dir: ProjectDir) -> EnvironmentDetail:
    env_path = _env_path(project_dir, name)
    if not env_path.exists():
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=_ENV_NOT_FOUND)
    env = load_environment(env_path)
    return EnvironmentDetail(name=env.name, variables=env.variables)


@router.put("/environments/{name}")
async def update_environment_route(
    name: str, body: EnvironmentDetail, project_dir: ProjectDir
) -> EnvironmentDetail:
    env_path = _env_path(project_dir, name)
    if not env_path.exists():
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=_ENV_NOT_FOUND)
    env = Environment(name=name, variables=body.variables)
    save_environment(env, project_dir)
    return EnvironmentDetail(name=env.name, variables=env.variables)
