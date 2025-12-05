import click
import os
import sys


@click.command()
def server():
    """Run Flask app using server.py"""

    server_path = "server.py"

    # check if server.py exists
    if not os.path.exists(server_path):
        click.echo("❌ Error: server.py tidak ditemukan di direktori saat ini!")
        sys.exit(1)

    click.echo("✔ server.py ditemukan, menjalankan Flask...")

    # run flask app using server.py
    os.system("flask --app server run --reload")
