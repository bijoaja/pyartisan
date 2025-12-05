import click
import os
import sys


@click.command()
def make_environment():
    """Generate .env from .env.example"""

    env_path = ".env.example"

    # 1. Check if .env.example exists
    if not os.path.exists(env_path):
        click.echo("❌ Error: .env.example not found!")
        sys.exit(1)

    click.echo("✔ .env.example found, creating a copy as .env...")

    # 2. Copy .env.example to .env if .env does not exist
    if not os.path.exists(".env"):
        os.system("cp .env.example .env")
        click.echo("✔ .env successfully created from .env.example")
    else:
        click.echo("⚠ .env already exists, not overwritten")