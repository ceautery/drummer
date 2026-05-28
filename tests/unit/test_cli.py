import click
import typer.main
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
    # Verify --port is registered; use Click introspection rather than parsing
    # rendered help text, which varies with terminal width/ANSI settings.
    click_group = typer.main.get_command(app)
    assert isinstance(click_group, click.Group)
    param_opts = [name for param in click_group.commands["serve"].params for name in param.opts]
    assert "--port" in param_opts


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
