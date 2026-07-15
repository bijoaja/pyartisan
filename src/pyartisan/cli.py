import sys

import click

from pyartisan import config as config_module
from pyartisan.context import ProjectContext
from pyartisan.exceptions import PluginNotFound
from pyartisan.plugin_loader import load_plugin
from pyartisan.shared.doctor import run_checks

__version__ = "1.0.0"


@click.group()
@click.version_option(__version__, prog_name="pyartisan")
def cli():
    """pyartisan - AI-powered Python Web Development Toolkit"""


@cli.command(name="init", context_settings={"ignore_unknown_options": True})
@click.argument("framework")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def init(framework: str, args: tuple) -> None:
    """Initialize a new project: pyartisan init <framework> <name>"""
    try:
        plugin = load_plugin(framework)
    except PluginNotFound as e:
        click.echo(f"❌ {e}")
        sys.exit(1)

    framework_cli = plugin.build_cli()
    if "init:project" not in framework_cli.commands:
        click.echo(f"❌ '{framework}' does not support project initialization yet.")
        sys.exit(1)

    framework_cli.main(
        args=["init:project", *args],
        prog_name=f"pyartisan init {framework}",
        standalone_mode=False,
    )


def _dispatch_to_framework(command_name: str, framework_option: str | None, args: list) -> None:
    """Shared dispatcher for make:* and other framework-owned subcommands.

    Resolves the framework (explicit --framework or auto-detected from cwd),
    then forwards to that framework plugin's own command implementation.
    """
    ctx_info = ProjectContext.resolve(explicit_framework=framework_option)
    if ctx_info.framework is None:
        click.echo("Project framework cannot be detected.")
        click.echo("Please specify:")
        click.echo("  --framework flask")
        sys.exit(1)

    try:
        plugin = load_plugin(ctx_info.framework)
    except PluginNotFound as e:
        click.echo(f"❌ {e}")
        sys.exit(1)

    framework_cli = plugin.build_cli()
    framework_cli.main(
        args=[command_name, *args],
        prog_name=f"pyartisan {command_name}",
        standalone_mode=False,
    )


@cli.command(name="make:controller", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--framework", default=None, help="Explicit framework override")
def make_controller_cmd(args, framework):
    """Generate a controller. Framework auto-detected unless --framework is given."""
    _dispatch_to_framework("make:controller", framework, list(args))


@cli.command(name="make:model", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--framework", default=None, help="Explicit framework override")
def make_model_cmd(args, framework):
    """Generate a model. Framework auto-detected unless --framework is given."""
    _dispatch_to_framework("make:model", framework, list(args))


@cli.command(name="make:service", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--framework", default=None, help="Explicit framework override")
def make_service_cmd(args, framework):
    """Generate a service. Framework auto-detected unless --framework is given."""
    _dispatch_to_framework("make:service", framework, list(args))


@cli.command(name="make:repository", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--framework", default=None, help="Explicit framework override")
def make_repository_cmd(args, framework):
    """Generate a repository. Framework auto-detected unless --framework is given."""
    _dispatch_to_framework("make:repository", framework, list(args))


@cli.command(name="make:migrations", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--framework", default=None, help="Explicit framework override")
def make_migrations_cmd(args, framework):
    """Run migrations. Framework auto-detected unless --framework is given."""
    _dispatch_to_framework("make:migrations", framework, list(args))


@cli.command(name="make:docker", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--framework", default=None, help="Explicit framework override")
def make_docker_cmd(args, framework):
    """Generate Docker files. Framework auto-detected unless --framework is given."""
    _dispatch_to_framework("make:docker", framework, list(args))


@cli.command(name="make:env", context_settings={"ignore_unknown_options": True})
@click.option("--framework", default=None, help="Explicit framework override")
def make_env_cmd(framework):
    """Copy .env.example to .env. Framework auto-detected unless --framework is given."""
    _dispatch_to_framework("make:env", framework, [])


@cli.command(name="serve", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--framework", default=None, help="Explicit framework override")
def serve_cmd(args, framework):
    """Run the dev server. Framework auto-detected unless --framework is given."""
    _dispatch_to_framework("serve", framework, list(args))


@cli.command(name="build", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.option("--framework", default=None, help="Explicit framework override")
def build_cmd(args, framework):
    """Build production Docker image. Framework auto-detected unless --framework is given."""
    _dispatch_to_framework("build", framework, list(args))


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
    """Set a single config key, e.g. pyartisan config set default_framework fastapi"""
    data = config_module.load()
    if key not in data:
        click.echo(f"❌ Unknown config key: {key}")
        sys.exit(1)
    data[key] = value
    config_module.save(data)
    click.echo(f"✔ {key} = {value}")


@cli.command(name="doctor")
def doctor():
    """Check Python, pip, Git, and virtual environment health."""
    ok = run_checks()
    if not ok:
        sys.exit(1)


@cli.command(name="version")
def version():
    """Show pyartisan version."""
    click.echo(f"pyartisan {__version__}")


if __name__ == "__main__":
    cli()
