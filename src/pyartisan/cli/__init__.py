import sys
import click

from pyartisan import __version__
from pyartisan import config as config_module
from pyartisan.core import engine
from pyartisan.core.exceptions import PyArtisanError
from pyartisan.shared.doctor import run_checks
from pyartisan.marketplace import plugin_group


@click.group()
@click.version_option(__version__, prog_name="pyartisan")
def cli():
    """pyartisan - AI-powered Python Web Development Toolkit"""


cli.add_command(plugin_group)


@cli.command(name="new")
@click.argument("framework")
@click.argument("name")
def new_cmd(framework: str, name: str) -> None:
    """Create a new project using framework template."""
    try:
        engine.dispatch_new(framework, name)
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)


@cli.command(name="make", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("target")
@click.argument("name")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing files")
@click.pass_context
def make_cmd(ctx, target: str, name: str, force: bool) -> None:
    """Scaffold files from template stubs (e.g. make controller Post)."""
    # Parse dynamic extra args: e.g. --type api --version 2
    extra_options = {}
    it = iter(ctx.args)
    for item in it:
        if item.startswith("--"):
            # Strip '--' and replace '-' with '_' for context keys
            key = item[2:].replace("-", "_")
            try:
                val = next(it)
                extra_options[key] = val
            except StopIteration:
                extra_options[key] = True  # boolean flag fallback
    try:
        engine.dispatch_make(target, name, force=force, **extra_options)
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)


@cli.command(name="serve")
def serve_cmd() -> None:
    """Run dev server (Docker fallback to local virtualenv)."""
    try:
        engine.dispatch_serve()
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)


@cli.command(name="build")
def build_cmd() -> None:
    """Build production artifact using manifest build script."""
    try:
        engine.dispatch_build()
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)


@cli.group(name="config", invoke_without_command=True)
@click.pass_context
def config_group(ctx):
    """Manage ~/.pyartisan/config.toml"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(config_show)


@config_group.command(name="show")
def config_show():
    """Print current configuration."""
    data = config_module.load()
    for key, value in data.items():
        click.echo(f"{key} = {value!r}")


@config_group.command(name="reset")
def config_reset():
    """Reset configuration to defaults."""
    config_module.reset()
    click.echo("✔ Configuration reset to defaults.")


@config_group.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a config key, e.g. pyartisan config set templates.flask <url>"""
    data = config_module.load()

    # Handle nested templates key
    if key.startswith("templates."):
        sub = key.split(".")[1]
        if "templates" not in data:
            data["templates"] = {}
        data["templates"][sub] = value
    else:
        if key not in data:
            click.echo(f"❌ Unknown config key: {key}")
            sys.exit(1)
        data[key] = value

    config_module.save(data)
    click.echo(f"✔ {key} = {value}")


@cli.command(name="doctor")
def doctor():
    """Check Python, pip, Git, and environment health."""
    ok = run_checks()
    if not ok:
        sys.exit(1)


@cli.command(name="version")
def version():
    """Show pyartisan version."""
    click.echo(f"pyartisan {__version__}")


if __name__ == "__main__":
    cli()
