import click
import os
import sys
import subprocess


def _is_venv_active() -> bool:
    return (
        os.environ.get("VIRTUAL_ENV") is not None
        or sys.prefix != sys.base_prefix
    )


def _docker_available() -> bool:
    try:
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _compose_command() -> list[str]:
    """Return the available docker compose command (plugin or standalone)."""
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return ["docker", "compose"]
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ["docker-compose"]


# =====================================================================
# Command
# =====================================================================

@click.command()
@click.option(
    "--docker",
    is_flag=True,
    default=False,
    help="Run the dev server inside Docker via docker compose up",
)
@click.option(
    "--build",
    "rebuild",
    is_flag=True,
    default=False,
    help="Force rebuild of Docker image before starting (only with --docker)",
)
def server(docker: bool, rebuild: bool) -> None:
    """Run Flask app using server.py with environment checks."""

    if docker:
        _run_docker(rebuild)
    else:
        _run_local()


def _run_local() -> None:
    """Start the Flask development server in the local environment."""

    if not os.path.exists("server.py") or not os.path.isfile(".env"):
        click.echo("Error: server.py or .env not found.")
        click.echo("Make sure you are in the project root directory and have created a .env file.")
        sys.exit(1)

    if not _is_venv_active():
        click.echo("Error: virtual environment not active.")
        click.echo("  Activate it first:")
        click.echo("    Mac/Linux: source venv/bin/activate")
        click.echo("    Windows:   venv\\Scripts\\activate")
        sys.exit(1)

    try:
        subprocess.check_output([sys.executable, "-m", "flask", "--version"])
    except Exception:
        click.echo("Error: Flask not found in the virtual environment.")
        click.echo("  Run: pip install flask")
        sys.exit(1)

    click.echo("server.py found")
    click.echo("virtual environment active")
    click.echo("Flask available")
    click.echo("Starting Flask dev server ...")

    try:
        subprocess.run(["flask", "--app", "server", "run", "--reload"])
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


def _run_docker(rebuild: bool) -> None:
    """Start the dev server via docker compose using Dockerfile.dev."""

    if not os.path.isfile("docker-compose.yml"):
        click.echo("Error: docker-compose.yml not found.")
        click.echo("  Run 'flasktool make:docker' first to generate it.")
        sys.exit(1)

    if not os.path.exists("Docker/Dockerfile.dev"):
        click.echo("Error: Docker/Dockerfile.dev not found.")
        click.echo("  Run 'flasktool make:docker' first to generate it.")
        sys.exit(1)

    if not _docker_available():
        click.echo("Error: Docker daemon is not running or Docker is not installed.")
        click.echo("  Start Docker Desktop or the Docker service and try again.")
        sys.exit(1)

    compose = _compose_command()

    cmd = compose + ["up"]
    if rebuild:
        cmd.append("--build")

    click.echo(f"Starting dev server with Docker ({' '.join(cmd)}) ...")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        click.echo("\nStopping containers ...")
        subprocess.run(compose + ["down"])
        click.echo("Containers stopped.")
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)
