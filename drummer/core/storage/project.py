from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from drummer.core.storage.formats import RequestFile, parse_request_file


class ProjectMeta(BaseModel):
    name: str
    version: str = "1"
    default_environment: str = "local"


class Environment(BaseModel):
    name: str
    variables: dict[str, str] = Field(default_factory=dict)


def load_project(project_dir: Path) -> ProjectMeta:
    config_path = project_dir / ".drummer" / "project.yaml"
    data: dict[str, object] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return ProjectMeta.model_validate(data)


def save_project(meta: ProjectMeta, project_dir: Path) -> None:
    config_path = project_dir / ".drummer" / "project.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.dump(meta.model_dump(mode="json"), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def create_project(project_dir: Path, name: str) -> ProjectMeta:
    meta = ProjectMeta(name=name)
    save_project(meta, project_dir)
    env_dir = project_dir / ".drummer" / "environments"
    env_dir.mkdir(parents=True, exist_ok=True)
    save_environment(Environment(name="local"), project_dir)
    return meta


def load_environment(path: Path) -> Environment:
    data: dict[str, object] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Environment.model_validate(data)


def save_environment(env: Environment, project_dir: Path) -> None:
    env_dir = project_dir / ".drummer" / "environments"
    env_dir.mkdir(parents=True, exist_ok=True)
    env_path = env_dir / f"{env.name}.yaml"
    env_path.write_text(
        yaml.dump(env.model_dump(mode="json"), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def list_environments(project_dir: Path) -> list[Environment]:
    env_dir = project_dir / ".drummer" / "environments"
    if not env_dir.exists():
        return []
    return [load_environment(path) for path in sorted(env_dir.glob("*.yaml"))]


def list_requests(project_dir: Path) -> list[Path]:
    drummer_dir = (project_dir / ".drummer").resolve()
    result: list[Path] = []
    for path in sorted(project_dir.rglob("*.md")):
        if path.resolve().is_relative_to(drummer_dir):
            continue
        try:
            parse_request_file(path)
        except (ValidationError, OSError, yaml.YAMLError):
            continue
        result.append(path)
    return result


def list_request_files(project_dir: Path) -> list[RequestFile]:
    drummer_dir = (project_dir / ".drummer").resolve()
    result: list[RequestFile] = []
    for path in sorted(project_dir.rglob("*.md")):
        if path.resolve().is_relative_to(drummer_dir):
            continue
        try:
            rf = parse_request_file(path)
        except (ValidationError, OSError, yaml.YAMLError):
            continue
        result.append(rf)
    return result
