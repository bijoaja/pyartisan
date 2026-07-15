from pathlib import Path

import click

from pyartisan.core.plugin_base import FrameworkPlugin
from pyartisan.core.detector import detect_framework

from flasktool.commands.make_controller import make_controller
from flasktool.commands.make_model import make_model
from flasktool.commands.make_repository import make_repository
from flasktool.commands.make_service import make_service
from flasktool.commands.make_migrations import make_migrations
from flasktool.commands.make_docker import make_docker
from flasktool.commands.make_env import make_environment
from flasktool.commands.init_project import init_project
from flasktool.commands.server import server
from flasktool.commands.build import build


class FlaskPlugin(FrameworkPlugin):
    name = "flask"

    @staticmethod
    def detect(path: Path) -> bool:
        return detect_framework(path) == "flask"

    def build_cli(self) -> click.Group:
        @click.group(name="flask")
        def flask_group():
            """Flask framework commands."""

        flask_group.add_command(init_project,     "init:project")
        flask_group.add_command(make_docker,      "make:docker")
        flask_group.add_command(make_controller,  "make:controller")
        flask_group.add_command(make_migrations,  "make:migrations")
        flask_group.add_command(make_model,       "make:model")
        flask_group.add_command(make_environment, "make:env")
        flask_group.add_command(make_service,     "make:service")
        flask_group.add_command(make_repository,  "make:repository")
        flask_group.add_command(server,           "serve")
        flask_group.add_command(build,            "build")
        return flask_group
