import sys
import click
from pyartisan.core import engine
from pyartisan.core.exceptions import PyArtisanError


@click.command(name="new")
@click.argument("framework")
@click.argument("name")
def new_cmd(framework: str, name: str) -> None:
    """Create a new project using framework template."""
    try:
        engine.dispatch_new(framework, name)
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)
