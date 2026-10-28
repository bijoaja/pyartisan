import sys

import click

from pyartisan.core import engine
from pyartisan.core.exceptions import PyArtisanError


@click.command(name="serve")
def serve_cmd() -> None:
    """Run dev server (Docker fallback to local virtualenv)."""
    try:
        engine.dispatch_serve()
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)
