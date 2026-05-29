from pathlib import Path

import pytest

from drummer.core.storage import workspaces as ws


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
    cfg = drummer_home / "projects" / "scratch" / ".drummer" / "project.yaml"
    assert cfg.exists()


def test_ensure_scratch_is_idempotent(drummer_home: Path) -> None:
    ws.ensure_scratch()
    ws.ensure_scratch()
    assert (drummer_home / "projects" / "scratch" / ".drummer" / "project.yaml").exists()


@pytest.mark.parametrize(
    ("name", "expected"), [("My API", "my-api"), ("acme_API!!", "acme-api"), ("   ", "workspace")]
)
def test_slugify(name: str, expected: str) -> None:
    assert ws.slugify(name) == expected
