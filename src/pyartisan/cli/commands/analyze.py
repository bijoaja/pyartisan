import sys

import click

from pyartisan.core import engine
from pyartisan.core.exceptions import PyArtisanError


@click.command(name="analyze")
@click.option("--only", multiple=True, help="Run only the specified check(s). Can be repeated.")
@click.option(
    "--fix",
    is_flag=True,
    default=False,
    help="Automatically fix issues where supported (e.g. ruff).",
)
def analyze_cmd(only: tuple[str, ...], fix: bool) -> None:
    """Run code quality and security checks (ruff, bandit, mypy)."""
    try:
        engine.dispatch_analyze(only=only, fix=fix)
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)
