from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from drummer import __version__
from drummer.api.app import create_app
from drummer.core.storage import workspaces
from drummer.core.storage.project import load_project

_ATTRIBUTION = (
    "Drummer includes data from the Metropolitan Museum of Art Open Access collection.\n"
    "License: Creative Commons Zero (CC0)\n"
    "Source: https://www.metmuseum.org/about-the-met/policies-and-documents/open-access\n"
    "The Met makes its Open Access data available for unrestricted use."
)

app = typer.Typer(name="drummer", help="Drummer — a local REST client.")

ProjectOpt = Annotated[
    str | None, typer.Option("--project", "-p", help="Open an external project folder.")
]
PortOpt = Annotated[int, typer.Option("--port", help="Port to listen on.")]
HostOpt = Annotated[str, typer.Option("--host", help="Host address to bind to.")]


def _launch(project: str | None, port: int, host: str) -> None:
    workspaces.ensure_scratch()
    if project is not None:
        info = workspaces.register_external(Path(project))
        workspaces.set_active(info.id)
        project_dir = Path(info.path)
    else:
        project_dir = workspaces.active_workspace_dir()
    application = create_app(project_dir=project_dir)
    meta = load_project(project_dir)
    typer.echo(f"Drummer serving '{meta.name}' on http://{host}:{port}")
    uvicorn.run(application, host=host, port=port)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    attribution: Annotated[
        bool, typer.Option("--attribution", help="Print dataset credits and exit.")
    ] = False,
    version: Annotated[
        bool, typer.Option("--version", "-V", help="Print version and exit.")
    ] = False,
    project: ProjectOpt = None,
    port: PortOpt = 8000,
    host: HostOpt = "127.0.0.1",
) -> None:
    if attribution:
        typer.echo(_ATTRIBUTION)
        raise typer.Exit()
    if version:
        typer.echo(f"Drummer {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        _launch(project, port, host)


@app.command(hidden=True)
def serve(project: ProjectOpt = None, port: PortOpt = 8000, host: HostOpt = "127.0.0.1") -> None:
    """Start the Drummer API server (alias for the bare `drummer` command)."""
    _launch(project, port, host)


@app.command()
def new(name: Annotated[str, typer.Argument(help="Name for the new workspace.")]) -> None:
    """Create a new central workspace under ~/.drummer/projects/."""
    info = workspaces.create_workspace(name)
    typer.echo(f"Created workspace '{info.name}' at {info.path}")


@app.command()
def export(path: Annotated[str, typer.Argument(help="Path of the project to export.")]) -> None:
    """Export a Drummer project at PATH as a zip file."""
    typer.echo(f"Exporting project at {path} ...")
    typer.echo("(Not yet implemented)")


@app.command()
def mcp() -> None:
    """Print MCP server connection info."""
    typer.echo("MCP server info: not yet implemented — Phase 4")


if __name__ == "__main__":
    app()
