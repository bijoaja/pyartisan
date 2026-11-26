import sys

import click

from pyartisan.core import engine
from pyartisan.core.exceptions import PyArtisanError


@click.command(name="serve")
@click.option("--docker", is_flag=True, default=False, help="Force dev server to run via Docker.")
@click.option("--venv", is_flag=True, default=False, help="Force dev server to run via local venv.")
@click.option("--uv", is_flag=True, default=False, help="Force dev server to run via uv.")
def serve_cmd(docker: bool, venv: bool, uv: bool) -> None:
    """Run dev server (Docker fallback to local virtualenv)."""
    flags = [name for name, val in [("docker", docker), ("venv", venv), ("uv", uv)] if val]
    if len(flags) > 1:
        raise click.UsageError("Cannot specify more than one serve mode.")
    mode = flags[0] if flags else None
    try:
        engine.dispatch_serve(mode=mode)
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)
