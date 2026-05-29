from pathlib import Path

import pytest

from drummer.core.storage import workspaces as ws
from drummer.core.storage.project import load_project


@pytest.fixture
def drummer_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("DRUMMER_HOME", str(tmp_path))
    return tmp_path


def test_home_respects_env_override(drummer_home: Path) -> None:
    assert ws.home() == drummer_home


def test_home_defaults_to_dot_drummer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DRUMMER_HOME", raising=False)
    assert ws.home() == Path.home() / ".drummer"


def test_ensure_scratch_creates_special_workspace(drummer_home: Path) -> None:
    ws.ensure_scratch()
    scratch = drummer_home / "projects" / "scratch"
    assert (scratch / ".drummer" / "project.yaml").exists()
    assert load_project(scratch).name == "Scratch"


def test_ensure_scratch_is_idempotent(drummer_home: Path) -> None:
    ws.ensure_scratch()
    ws.ensure_scratch()
    assert (drummer_home / "projects" / "scratch" / ".drummer" / "project.yaml").exists()


@pytest.mark.parametrize(
    ("name", "expected"), [("My API", "my-api"), ("acme_API!!", "acme-api"), ("   ", "workspace")]
)
def test_slugify(name: str, expected: str) -> None:
    assert ws.slugify(name) == expected


def test_list_workspaces_scratch_first(drummer_home: Path) -> None:
    ws.create_workspace("Zebra API")
    ws.create_workspace("Alpha API")
    result = ws.list_workspaces()
    assert result[0].is_scratch is True
    assert result[0].id == "scratch"
    assert [w.name for w in result[1:]] == ["Alpha API", "Zebra API"]


def test_create_workspace_central(drummer_home: Path) -> None:
    info = ws.create_workspace("My API")
    assert info.id == "my-api"
    assert info.kind == "central"
    assert info.is_scratch is False
    assert (Path(info.path) / ".drummer" / "project.yaml").exists()


def test_create_workspace_rejects_duplicate(drummer_home: Path) -> None:
    ws.create_workspace("My API")
    with pytest.raises(ValueError, match="already exists"):
        ws.create_workspace("my api")


def test_register_external_initializes_and_lists(drummer_home: Path, tmp_path: Path) -> None:
    external = tmp_path / "outside-repo"
    external.mkdir()
    info = ws.register_external(external)
    assert info.kind == "external"
    assert info.id == str(external.resolve())
    assert (external / ".drummer" / "project.yaml").exists()
    ids = [w.id for w in ws.list_workspaces()]
    assert str(external.resolve()) in ids


def test_register_external_is_deduped(drummer_home: Path, tmp_path: Path) -> None:
    external = tmp_path / "repo"
    external.mkdir()
    ws.register_external(external)
    ws.register_external(external)
    externals = [w for w in ws.list_workspaces() if w.kind == "external"]
    assert len(externals) == 1


def test_get_active_defaults_to_scratch(drummer_home: Path) -> None:
    assert ws.get_active() == "scratch"


def test_set_and_get_active(drummer_home: Path) -> None:
    ws.create_workspace("My API")
    ws.set_active("my-api")
    assert ws.get_active() == "my-api"


def test_get_active_falls_back_when_missing(drummer_home: Path) -> None:
    ws.set_active("does-not-exist")
    assert ws.get_active() == "scratch"


def test_resolve_workspace_central_vs_external(drummer_home: Path, tmp_path: Path) -> None:
    assert ws.resolve_workspace("scratch") == drummer_home / "projects" / "scratch"
    ext = tmp_path / "ext"
    assert ws.resolve_workspace(str(ext)) == ext
