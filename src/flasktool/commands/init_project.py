import click
import os
import subprocess


@click.command()
@click.argument("project_name")
def init_project(project_name):
    """Clone initial project template from GitHub using bash command"""

    repo_url = "https://github.com/bijoaja/flaskiq.git"

    # Check if folder already exists
    if os.path.exists(project_name):
        click.echo("❌ Folder already exists, choose a different name.")
        return

    click.echo(f"⬇ Cloning {repo_url} ...")

    try:
        # Run git clone command
        result = subprocess.run(
            ["git", "clone", repo_url, project_name],
            capture_output=True,
            text=True
        )

        # Check if cloning was successful
        if result.returncode != 0:
            click.echo("❌ Failed to clone project!")
            click.echo(result.stderr)
            return

        click.echo(f"✔ Project initialized in: {project_name}")

    except FileNotFoundError:
        click.echo("❌ Git not found! Install Git first.")
