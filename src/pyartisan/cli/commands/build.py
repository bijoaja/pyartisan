import sys

import click

from pyartisan.core import engine
from pyartisan.core.exceptions import PyArtisanError


@click.command(name="build")
def build_cmd() -> None:
    """Build production artifact using manifest build script."""
    try:
        engine.dispatch_build()
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)
