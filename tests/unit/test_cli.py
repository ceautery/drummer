import click
from typer.testing import CliRunner

from drummer.cli import app
from drummer.core.storage.project import create_project

runner = CliRunner()


def test_help_shows_drummer():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Drummer" in result.output


def test_serve_command_exists():
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    # Strip ANSI before checking — CI may render with character-level escape codes
    # that break contiguous substring matches.
    assert "--port" in click.unstyle(result.output)


def test_new_command_exists():
    result = runner.invoke(app, ["new", "--help"])
    assert result.exit_code == 0


def test_export_command_exists():
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0


def test_mcp_command_exists():
    result = runner.invoke(app, ["mcp", "--help"])
    assert result.exit_code == 0


def test_attribution_option_exists():
    result = runner.invoke(app, ["--attribution"])
    assert result.exit_code == 0
    assert "Metropolitan Museum" in result.output


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_bare_drummer_launches_server(monkeypatch, tmp_path):
    monkeypatch.setenv("DRUMMER_HOME", str(tmp_path))
    calls = {}

    def fake_run(application, host, port):
        calls["host"] = host
        calls["port"] = port

    monkeypatch.setattr("drummer.cli.uvicorn.run", fake_run)
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert calls["port"] == 8000


def test_new_creates_central_workspace(monkeypatch, tmp_path):
    monkeypatch.setenv("DRUMMER_HOME", str(tmp_path))
    result = runner.invoke(app, ["new", "My API"])
    assert result.exit_code == 0
    assert (tmp_path / "projects" / "my-api" / ".drummer" / "project.yaml").exists()


def test_project_flag_registers_and_launches(monkeypatch, tmp_path):
    monkeypatch.setenv("DRUMMER_HOME", str(tmp_path))
    ext = tmp_path / "my-ext-project"
    ext.mkdir()
    create_project(ext, "My Ext")

    calls = {}

    def fake_run(application, host, port):
        calls["ran"] = True

    monkeypatch.setattr("drummer.cli.uvicorn.run", fake_run)
    result = runner.invoke(app, ["--project", str(ext)])
    assert result.exit_code == 0
    assert calls.get("ran") is True
    assert "My Ext" in result.output


def test_project_flag_initializes_new_project(monkeypatch, tmp_path):
    monkeypatch.setenv("DRUMMER_HOME", str(tmp_path))
    ext = tmp_path / "fresh-project"
    ext.mkdir()

    monkeypatch.setattr("drummer.cli.uvicorn.run", lambda *_args, **_kwargs: None)
    result = runner.invoke(app, ["--project", str(ext)])
    assert result.exit_code == 0
    assert "Initialized a new Drummer project" in result.output
