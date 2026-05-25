from typer.testing import CliRunner

from drummer.cli import app

runner = CliRunner()


def test_help_shows_drummer():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Drummer" in result.output


def test_serve_command_exists():
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output


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
