import sys
from typing import Any

import click

from pyartisan.core import engine
from pyartisan.core.exceptions import PyArtisanError


@click.command(
    name="make", context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
@click.argument("target")
@click.argument("name")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing files")
@click.pass_context
def make_cmd(ctx: click.Context, target: str, name: str, force: bool) -> None:
    """Scaffold files from template stubs (e.g. make controller Post)."""
    extra_options: dict[str, Any] = {}
    it = iter(ctx.args)
    for item in it:
        if item.startswith("--"):
            key = item[2:].replace("-", "_")
            try:
                val = next(it)
                extra_options[key] = val
            except StopIteration:
                extra_options[key] = True
    try:
        engine.dispatch_make(target, name, force=force, **extra_options)
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)
