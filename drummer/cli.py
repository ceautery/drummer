from pathlib import Path
from typing import Annotated

import typer
import uvicorn

from drummer import __version__
from drummer.api.app import create_app

_ATTRIBUTION = (
    "Drummer includes data from the Metropolitan Museum of Art Open Access collection.\n"
    "License: Creative Commons Zero (CC0)\n"
    "Source: https://www.metmuseum.org/about-the-met/policies-and-documents/open-access\n"
    "The Met makes its Open Access data available for unrestricted use."
)

app = typer.Typer(name="drummer", help="Drummer — a local REST client.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    attribution: Annotated[
        bool, typer.Option("--attribution", help="Print dataset credits and exit.")
    ] = False,
    version: Annotated[
        bool, typer.Option("--version", "-V", help="Print version and exit.")
    ] = False,
) -> None:
    if attribution:
        typer.echo(_ATTRIBUTION)
        raise typer.Exit()
    if version:
        typer.echo(f"Drummer {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def serve(
    project: Annotated[
        str | None, typer.Option("--project", "-p", help="Path to the project folder.")
    ] = None,
    port: Annotated[int, typer.Option("--port", help="Port to listen on.")] = 8000,
    host: Annotated[str, typer.Option("--host", help="Host address to bind to.")] = "127.0.0.1",
) -> None:
    """Start the Drummer API server, optionally loading PROJECT on startup."""
    project_dir: Path | None = None
    if project is not None:
        project_dir = Path(project).expanduser().resolve()
        if not (project_dir / ".drummer" / "project.yaml").exists():
            typer.echo(
                f"Error: {project_dir} is not a Drummer project (missing .drummer/project.yaml)",
                err=True,
            )
            raise typer.Exit(code=1)

    application = create_app(project_dir=project_dir)
    label = project_dir.name if project_dir is not None else "(no project)"
    typer.echo(f"Drummer serving {label} on http://{host}:{port}")
    uvicorn.run(application, host=host, port=port)


@app.command()
def new(path: Annotated[str, typer.Argument(help="Path for the new project folder.")]) -> None:
    """Create a new Drummer project at PATH."""
    typer.echo(f"Creating project at {path} ...")
    typer.echo("(Not yet implemented — Phase 2)")


@app.command()
def export(path: Annotated[str, typer.Argument(help="Path of the project to export.")]) -> None:
    """Export a Drummer project at PATH as a zip file."""
    typer.echo(f"Exporting project at {path} ...")
    typer.echo("(Not yet implemented — Phase 2)")


@app.command()
def mcp() -> None:
    """Print MCP server connection info."""
    typer.echo("MCP server info: not yet implemented — Phase 4")
