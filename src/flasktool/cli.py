import click
from flasktool.commands.make_controller import make_controller
from flasktool.commands.make_model import make_model
from flasktool.commands.server import server
from flasktool.commands.build import build
from flasktool.commands.make_docker import make_docker
from flasktool.commands.init_project import init_project
from flasktool.commands.make_env import make_environment
from flasktool.commands.make_migrations import make_migrations


@click.group()
def cli():
    """flasktool - Artisan-like CLI for Flask"""
    pass


cli.add_command(init_project, "init:project")
cli.add_command(make_docker, "make:docker")
cli.add_command(make_controller, "make:controller")
cli.add_command(make_migrations, "make:migrations")
cli.add_command(make_model, "make:model")
cli.add_command(make_environment, "make:env")
cli.add_command(server, "serve")
cli.add_command(build, "build")
