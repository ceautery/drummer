from typing import Annotated

import typer

from drummer import __version__

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
    port: Annotated[int, typer.Option("--port", "-p", help="Port to listen on.")] = 8000,
) -> None:
    """Start the Drummer server and open the browser."""
    typer.echo(f"Starting Drummer on http://localhost:{port} ...")
    typer.echo("(Server not yet implemented — Phase 4)")


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
