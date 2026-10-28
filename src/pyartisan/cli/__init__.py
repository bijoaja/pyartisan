import sys
from typing import Any

import click

from pyartisan import __version__
from pyartisan.cli.commands import (
    build_cmd,
    config_group,
    doctor_cmd,
    make_cmd,
    new_cmd,
    plugin_group,
    serve_cmd,
    version_cmd,
)


def _force_utf8(*streams: Any) -> None:
    """Output uses symbols like ✔ and ❌; legacy Windows codepages (cp1252) crash on them."""
    for s in streams or (sys.stdout, sys.stderr):
        if (
            s is not None
            and (getattr(s, "encoding", None) or "").lower().replace("-", "") != "utf8"
        ):
            try:
                s.reconfigure(encoding="utf-8")
            except (AttributeError, ValueError):
                pass  # not a TextIOWrapper (e.g. replaced stream); leave as is


# Run at import so it also covers `--help` and errors raised before the group callback.
_force_utf8()


@click.group()
@click.version_option(__version__, prog_name="pyartisan")
def cli() -> None:
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
