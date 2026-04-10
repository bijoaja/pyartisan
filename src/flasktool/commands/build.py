import click
import os


@click.command()
@click.option('--image-name', prompt='Enter the Docker image name', help='Name of the Docker image to build')
def build(image_name: str="myapp:latest"):
    """Build docker for project with a specified image name"""

    if not os.path.exists("Docker/Dockerfile") or not os.path.isfile("docker-compose.yml"):
        click.echo("❌ Dockerfile not found. Run 'make:docker' first.")
        return

    click.echo(f"🔄 Building Docker image: {image_name}...")
    os.system(f"docker build -t {image_name} .")
