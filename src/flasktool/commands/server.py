import click
import os
import sys
import subprocess


def is_venv_active():
    """Check if Python virtual environment is active."""
    return (
        os.environ.get("VIRTUAL_ENV") is not None
        or sys.prefix != sys.base_prefix
    )



@click.command()
def server():
    """Run Flask app using server.py with environment checks."""

    server_path = "server.py"

    # 1. Check server.py exists and .env file exists
    if not os.path.exists(server_path) or not os.path.isfile(".env"):
        click.echo("❌ Error: server.py or .env not found!")
        click.echo("Make sure you are in the project root directory. or you have created .env file.")
        sys.exit(1)

    # 2. Check venv active
    if not is_venv_active():
        click.echo("❌ Error: Virtual environment not active!")
        click.echo("   Activate it first:")
        click.echo("   - Windows:   venv\\Scripts\\activate")
        click.echo("   - Mac/Linux: source venv/bin/activate")
        sys.exit(1)

    # 3. Check flask is installed inside venv
    try:
        subprocess.check_output([sys.executable, "-m", "flask", "--version"])
    except Exception:
        click.echo("❌ Error: Flask not found in virtual environment!")
        click.echo("   Install Flask first:")
        click.echo("   pip install flask")
        sys.exit(1)

    click.echo("✔ server.py found")
    click.echo("✔ Virtual environment active")
    click.echo("✔ Flask available in environment")
    click.echo("🚀 Running Flask server...")

    # 4. Run Flask safely (better than os.system)
    try:
        subprocess.run(["flask", "--app", "server", "run", "--reload"])
    except KeyboardInterrupt:
        click.echo("\n🛑 Server stopped")
    except Exception as e:
        click.echo(f"❌ Error occurred while running Flask: {str(e)}")
        sys.exit(1)
