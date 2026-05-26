from pathlib import Path

import pytest
from pydantic import ValidationError

from drummer.core.storage.project import ProjectMeta, create_project, load_project, save_project


def test_create_project_creates_files(tmp_path: Path) -> None:
    meta = create_project(tmp_path, "My API")
    assert meta.name == "My API"
    assert meta.version == "1"
    assert meta.default_environment == "local"
    assert (tmp_path / ".drummer" / "project.yaml").exists()
    assert (tmp_path / ".drummer" / "environments" / "local.yaml").exists()


def test_load_project_roundtrip(tmp_path: Path) -> None:
    create_project(tmp_path, "My API")
    meta = load_project(tmp_path)
    assert meta.name == "My API"
    assert meta.default_environment == "local"


def test_save_project_updates_yaml(tmp_path: Path) -> None:
    create_project(tmp_path, "Original")
    meta = ProjectMeta(name="Updated", default_environment="staging")
    save_project(meta, tmp_path)
    loaded = load_project(tmp_path)
    assert loaded.name == "Updated"
    assert loaded.default_environment == "staging"


def test_project_meta_defaults() -> None:
    meta = ProjectMeta(name="Test")
    assert meta.version == "1"
    assert meta.default_environment == "local"


def test_create_project_missing_name_raises() -> None:
    with pytest.raises(ValidationError):
        ProjectMeta.model_validate({"version": "1"})
