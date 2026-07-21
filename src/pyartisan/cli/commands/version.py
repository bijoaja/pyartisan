import click
from pyartisan import __version__


@click.command(name="version")
def version_cmd() -> None:
    """Show pyartisan version."""
    click.echo(f"pyartisan {__version__}")
