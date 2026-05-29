"""Workspace storage: paths, scratch bootstrap, slug helpers, and the WorkspaceInfo model."""

import os
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from drummer.core.storage.project import create_project, project_exists


class WorkspaceInfo(BaseModel):
    id: str  # central slug, or absolute path for external workspaces
    name: str
    kind: Literal["central", "external"]
    path: str
    is_scratch: bool


def home() -> Path:
    override = os.environ.get("DRUMMER_HOME")
    return Path(override) if override else Path.home() / ".drummer"


def _projects_dir() -> Path:
    return home() / "projects"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "workspace"


def ensure_scratch() -> None:
    scratch = _projects_dir() / "scratch"
    if not project_exists(scratch):
        scratch.mkdir(parents=True, exist_ok=True)
        create_project(scratch, "Scratch")
