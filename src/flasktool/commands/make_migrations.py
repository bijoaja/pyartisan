import click
import subprocess
import os

@click.command(name="make:migrations")
@click.option("--message", "-m", default="", help="Migration message", required=True)
@click.option("--upgrade", is_flag=True, default=False, help="Run upgrade after migrate")
def make_migrations(message, upgrade: bool=False):
    """
    Create Flask-Migrate migrations and optionally upgrade the database.
    """

    os.makedirs("instance", exist_ok=True)

    # 1. Cek apakah folder migrations sudah ada
    if not os.path.exists("migrations"):
        click.echo("🔧 Initializing migrations...")
        try:
            subprocess.run(["flask", "db", "init"], check=True)
        except subprocess.CalledProcessError:
            click.echo("⚠️  Migrations folder already exists. Skipping init.")
        except Exception as e:
            click.echo(f"❌ Error during migrations init: {e}")
            return

    # 2. Jalankan migrate
    click.echo("📦 Running migration...")
    try:
        subprocess.run(["flask", "db", "migrate", "-m", message], check=True)
    except subprocess.CalledProcessError:
        click.echo("⚠️  No changes detected. Migration skipped.")
    except Exception as e:
        click.echo(f"❌ Error during migration: {e}")
        return

    # 3. Jika type = upgrade → jalankan upgrade DB
    if upgrade:
        click.echo("🚀 Upgrading database...")
        try:
            subprocess.run(["flask", "db", "upgrade"], check=True)
        except Exception as e:
            click.echo(f"❌ Error during database upgrade: {e}")
            return
        
    click.echo("✅ Migration command completed.")
