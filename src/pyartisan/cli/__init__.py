import click

from pyartisan import __version__
from pyartisan.cli.commands import (
    new_cmd,
    make_cmd,
    serve_cmd,
    build_cmd,
    config_group,
    doctor_cmd,
    version_cmd,
    plugin_group,
)


@click.group()
@click.version_option(__version__, prog_name="pyartisan")
def cli():
    """pyartisan - AI-powered Python Web Development Toolkit"""
    pass


cli.add_command(new_cmd)
cli.add_command(make_cmd)
cli.add_command(serve_cmd)
cli.add_command(build_cmd)
cli.add_command(config_group)
cli.add_command(doctor_cmd)
cli.add_command(version_cmd)
cli.add_command(plugin_group)


if __name__ == "__main__":
    cli()
