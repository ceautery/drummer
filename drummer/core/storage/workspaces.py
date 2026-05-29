"""Workspace storage: paths, scratch bootstrap, slug helpers, and the WorkspaceInfo model."""

import os
import re
from pathlib import Path
from typing import Literal, cast

import yaml
from pydantic import BaseModel

from drummer.core.storage.project import create_project, load_project, project_exists


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


def _config_path() -> Path:
    return home() / "config.yaml"


def _registry_path() -> Path:
    return home() / "registry.yaml"


def ensure_scratch() -> None:
    scratch = _projects_dir() / "scratch"
    if not project_exists(scratch):
        scratch.mkdir(parents=True, exist_ok=True)
        create_project(scratch, "Scratch")


def _read_registry() -> list[str]:
    path = _registry_path()
    if not path.exists():
        return []
    data: dict[str, object] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    external = data.get("external")
    if not isinstance(external, list):
        return []
    return [str(item) for item in cast("list[object]", external)]


def _write_registry(external: list[str]) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump({"external": external}, default_flow_style=False), encoding="utf-8")


def _central_workspaces() -> list[WorkspaceInfo]:
    result: list[WorkspaceInfo] = []
    pdir = _projects_dir()
    if not pdir.exists():
        return result
    for child in sorted(pdir.iterdir()):
        if not project_exists(child):
            continue
        meta = load_project(child)
        result.append(
            WorkspaceInfo(
                id=child.name,
                name=meta.name,
                kind="central",
                path=str(child.resolve()),
                is_scratch=child.name == "scratch",
            )
        )
    return result


def _external_workspaces() -> list[WorkspaceInfo]:
    result: list[WorkspaceInfo] = []
    for raw in _read_registry():
        path = Path(raw)
        if not project_exists(path):
            continue
        meta = load_project(path)
        result.append(
            WorkspaceInfo(
                id=str(path.resolve()),
                name=meta.name,
                kind="external",
                path=str(path.resolve()),
                is_scratch=False,
            )
        )
    return result


def list_workspaces() -> list[WorkspaceInfo]:
    ensure_scratch()
    central = _central_workspaces()
    scratch = [w for w in central if w.is_scratch]
    others = sorted((w for w in central if not w.is_scratch), key=lambda w: w.name.lower())
    return scratch + others + _external_workspaces()


def create_workspace(name: str) -> WorkspaceInfo:
    slug = slugify(name)
    target = _projects_dir() / slug
    if project_exists(target):
        msg = f"Workspace '{slug}' already exists"
        raise ValueError(msg)
    target.mkdir(parents=True, exist_ok=True)
    create_project(target, name)
    return WorkspaceInfo(
        id=slug, name=name, kind="central", path=str(target.resolve()), is_scratch=False
    )


def register_external(path: Path) -> WorkspaceInfo:
    resolved = path.expanduser().resolve()
    if not project_exists(resolved):
        resolved.mkdir(parents=True, exist_ok=True)
        create_project(resolved, resolved.name)
    registry = _read_registry()
    if str(resolved) not in registry:
        registry.append(str(resolved))
        _write_registry(registry)
    meta = load_project(resolved)
    return WorkspaceInfo(
        id=str(resolved), name=meta.name, kind="external", path=str(resolved), is_scratch=False
    )


def resolve_workspace(workspace_id: str) -> Path:
    candidate = Path(workspace_id)
    return candidate if candidate.is_absolute() else _projects_dir() / workspace_id


def workspace_info(workspace_id: str) -> WorkspaceInfo:
    target = resolve_workspace(workspace_id)
    meta = load_project(target)
    is_external = Path(workspace_id).is_absolute()
    return WorkspaceInfo(
        id=workspace_id,
        name=meta.name,
        kind="external" if is_external else "central",
        path=str(target.resolve()),
        is_scratch=not is_external and workspace_id == "scratch",
    )


def _workspace_exists(workspace_id: str) -> bool:
    return project_exists(resolve_workspace(workspace_id))


def get_active() -> str:
    path = _config_path()
    if path.exists():
        data: dict[str, object] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        active = data.get("active_workspace")
        if isinstance(active, str) and _workspace_exists(active):
            return active
    return "scratch"


def set_active(workspace_id: str) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, object] = {}
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data["active_workspace"] = workspace_id
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def active_workspace_dir() -> Path:
    ensure_scratch()
    return resolve_workspace(get_active())
