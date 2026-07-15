from pathlib import Path

import click

from pyartisan.core.plugin_base import FrameworkPlugin
from pyartisan.core.detector import detect_framework


class FastAPIPlugin(FrameworkPlugin):
    name = "fastapi"

    @staticmethod
    def detect(path: Path) -> bool:
        return detect_framework(path) == "fastapi"

    def build_cli(self) -> click.Group:
        @click.group(name="fastapi")
        def fastapi_group():
            """FastAPI framework commands (generators coming in a future release)."""

        @fastapi_group.command(name="status")
        def status():
            """Report that FastAPI generators are not yet implemented."""
            click.echo(
                "FastAPI plugin structure is registered; generator commands "
                "are not implemented yet (see PRD.md roadmap)."
            )

        return fastapi_group
