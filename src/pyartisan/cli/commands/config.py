import sys

import click

from pyartisan import config as config_module
from pyartisan.core.exceptions import PyArtisanError
from pyartisan.utils.safe import validate_clone_url, validate_name


@click.group(name="config", invoke_without_command=True)
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

    if key.startswith("templates."):
        sub = key.split(".", 1)[1]
        try:
            validate_name(sub, "template name")
            validate_clone_url(value, "template URL")
        except PyArtisanError as e:
            raise click.ClickException(str(e))
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
