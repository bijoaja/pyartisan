import sys

import click

from pyartisan.shared.doctor import run_checks


@click.command(name="doctor")
@click.option(
    "--upgrade",
    is_flag=True,
    default=False,
    help="Prompt to upgrade outdated dependencies.",
)
def doctor_cmd(upgrade: bool) -> None:
    """Check Python, pip, Git, and environment health."""
    ok = run_checks(upgrade=upgrade)
    if not ok:
        sys.exit(1)
