from pathlib import Path

import pytest
from pydantic import ValidationError

from drummer.core.storage.project import (
    Environment,
    ProjectMeta,
    create_project,
    list_environments,
    list_requests,
    load_environment,
    load_project,
    save_environment,
    save_project,
)


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


def test_environment_defaults() -> None:
    env = Environment(name="local")
    assert env.variables == {}


def test_save_and_load_environment(tmp_path: Path) -> None:
    create_project(tmp_path, "Test")
    auth_value = "abc123"
    env = Environment(
        name="staging", variables={"base_url": "https://staging.example.com", "auth": auth_value}
    )
    save_environment(env, tmp_path)
    loaded = load_environment(tmp_path / ".drummer" / "environments" / "staging.yaml")
    assert loaded.name == "staging"
    assert loaded.variables["base_url"] == "https://staging.example.com"
    assert loaded.variables["auth"] == auth_value


def test_list_environments_returns_all(tmp_path: Path) -> None:
    create_project(tmp_path, "Test")  # creates local env
    staging_url = "https://staging.example.com"
    prod_url = "https://prod.example.com"
    save_environment(Environment(name="staging", variables={"url": staging_url}), tmp_path)
    save_environment(Environment(name="prod", variables={"url": prod_url}), tmp_path)
    envs = list_environments(tmp_path)
    names = {e.name for e in envs}
    assert names == {"local", "staging", "prod"}


def test_list_environments_empty_dir(tmp_path: Path) -> None:
    (tmp_path / ".drummer" / "environments").mkdir(parents=True)
    envs = list_environments(tmp_path)
    assert envs == []


def test_list_environments_missing_dir(tmp_path: Path) -> None:
    envs = list_environments(tmp_path)
    assert envs == []


def test_list_requests_finds_valid_files(tmp_path: Path) -> None:
    create_project(tmp_path, "Test")
    (tmp_path / "get-users.md").write_text(
        "---\nname: Get Users\nmethod: GET\nurl: https://api.example.com/users\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "auth").mkdir()
    (tmp_path / "auth" / "login.md").write_text(
        "---\nname: Login\nmethod: POST\nurl: https://api.example.com/login\n---\n",
        encoding="utf-8",
    )
    paths = list_requests(tmp_path)
    names = {p.name for p in paths}
    assert names == {"get-users.md", "login.md"}


def test_list_requests_skips_non_request_md(tmp_path: Path) -> None:
    create_project(tmp_path, "Test")
    (tmp_path / "README.md").write_text("# My API\n\nNo frontmatter here.\n", encoding="utf-8")
    (tmp_path / "request.md").write_text(
        "---\nname: Valid Request\nmethod: GET\nurl: https://api.example.com\n---\n",
        encoding="utf-8",
    )
    paths = list_requests(tmp_path)
    assert len(paths) == 1
    assert paths[0].name == "request.md"


def test_list_requests_excludes_drummer_dir(tmp_path: Path) -> None:
    create_project(tmp_path, "Test")
    # Place a structurally valid .md inside .drummer/ — must be excluded
    internal = tmp_path / ".drummer" / "notes.md"
    internal.write_text(
        "---\nname: Internal\nmethod: GET\nurl: https://api.example.com\n---\n", encoding="utf-8"
    )
    (tmp_path / "request.md").write_text(
        "---\nname: Real Request\nmethod: GET\nurl: https://api.example.com\n---\n",
        encoding="utf-8",
    )
    paths = list_requests(tmp_path)
    assert len(paths) == 1
    assert paths[0].name == "request.md"


def test_list_requests_empty_project(tmp_path: Path) -> None:
    create_project(tmp_path, "Empty")
    paths = list_requests(tmp_path)
    assert paths == []


def test_list_requests_returns_sorted(tmp_path: Path) -> None:
    create_project(tmp_path, "Test")
    for name in ["c-request.md", "a-request.md", "b-request.md"]:
        (tmp_path / name).write_text(
            f"---\nname: {name}\nmethod: GET\nurl: https://api.example.com\n---\n", encoding="utf-8"
        )
    paths = list_requests(tmp_path)
    assert [p.name for p in paths] == ["a-request.md", "b-request.md", "c-request.md"]
