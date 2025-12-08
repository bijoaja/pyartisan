import click
import os
import subprocess
import sys
import shutil


@click.command()
@click.argument("project_name")
def init_project(project_name):
    """Initialize new FlaskIQ project with venv + dependency install."""

    repo_url = "https://github.com/bijoaja/flaskiq.git"

    # 1. Folder check
    if os.path.exists(project_name):
        click.echo("❌ Folder already exists, choose a different name.")
        return

    click.echo(f"⬇ Cloning the repository ...")


    # 2. Clone repo
    try:
        result = subprocess.run(
            ["git", "clone", repo_url, project_name],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            click.echo("❌ Failed to clone project!")
            click.echo(result.stderr)
            return

        click.echo(f"✔ Project cloned into: {project_name}")
        
        git_command = subprocess.run(
            ["git", "remote", "rm", "origin"],
            cwd=project_name,
            capture_output=True,
            text=True
        )

        if git_command.returncode == 0:
            click.echo("✔ Add your own remote repository later.")

    except FileNotFoundError:
        click.echo("❌ Git not found! Install Git first.")
        return
    
    install_dependencies = click.confirm("Do you want to create a virtual environment and install dependencies now?", default=True)
    if not install_dependencies:
        click.echo("⚠ Skipping virtual environment and dependency installation.")
        click.echo("Install dependencies is required to run the project.")

    else:
        # Change directory to project
        os.chdir(project_name)

        # 3. Create virtual environment
        click.echo("⚙ Creating virtual environment (venv)...")

        try:
            venv_cmd = [sys.executable, "-m", "venv", "venv"]
            subprocess.run(venv_cmd, check=True)

            click.echo("✔ Virtual environment created successfully.")
        except Exception as e:
            click.echo(f"❌ Failed to create venv: {e}")
            return

        # Determine venv python path (cross-platform)
        venv_python = (
            "venv\\Scripts\\python.exe" if os.name == "nt" else "venv/bin/python"
        )

        # 4. Install dependencies
        req_file = "requirements.txt"

        if not os.path.exists(req_file):
            click.echo("⚠ requirements.txt not found, skipping dependency installation.")
            return

        click.echo("📦 Installing dependencies from requirements.txt ...")

        try:
            install_cmd = [venv_python, "-m", "pip", "install", "-r", req_file]
            subprocess.run(install_cmd, check=True)

            click.echo("✔ Dependencies installed successfully.")

        except Exception as e:
            click.echo(f"❌ Failed to install dependencies: {e}")
            return

    # 5. Success message
    click.echo("\n🎉 Project initialization complete!")
    click.echo("👉 Activate your environment:")

    # 6. Enter the directory
    click.echo(f"   cd {project_name}")
    
    if os.name == "nt":
        click.echo("   venv\\Scripts\\activate")
    else:
        click.echo("   source venv/bin/activate")

    click.echo("\n👉 Run the server:")
    click.echo("   flasktool serve\n")
