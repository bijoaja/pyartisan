import sys

import click

from pyartisan.shared.doctor import run_checks


@click.command(name="doctor")
def doctor_cmd() -> None:
    """Check Python, pip, Git, and environment health."""
    ok = run_checks()
    if not ok:
        sys.exit(1)
