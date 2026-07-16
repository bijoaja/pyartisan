import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
import click

from pyartisan.core.manifest import load_manifest
from pyartisan.core.exceptions import GeneratorNotSupported, TemplateNotFound, ManifestError
from pyartisan.renderer import render_stub
from pyartisan.core.registration import apply_registration
from pyartisan.utils.naming import name_parts
from pyartisan import config as config_module


def dispatch_new(framework: str, project_name: str) -> None:
    """Initialize a new project by cloning the framework template."""
    config_data = config_module.load()
    templates = config_data.get("templates", {
        "flask": "https://github.com/bijoaja/flaskiq.git",
        "fastapi": "https://github.com/bijoaja/fastiq.git",
    })

    if framework not in templates:
        raise TemplateNotFound(
            f"No template registered for framework '{framework}'. "
            f"Available: {', '.join(templates.keys())}"
        )

    repo_url = templates[framework]

    if os.path.exists(project_name):
        click.echo(f"❌ Folder '{project_name}' already exists, choose a different name.")
        sys.exit(1)

    click.echo(f"⬇ Cloning {framework} template repository ...")
    try:
        result = subprocess.run(
            ["git", "clone", repo_url, project_name],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            click.echo("❌ Failed to clone project!")
            click.echo(result.stderr)
            sys.exit(1)

        click.echo(f"✔ Project cloned into: {project_name}")
        subprocess.run(["git", "remote", "rm", "origin"], cwd=project_name, capture_output=True)
    except FileNotFoundError:
        click.echo("❌ Git not found! Install Git first.")
        sys.exit(1)

    install_dependencies = click.confirm(
        "Do you want to create a virtual environment and install dependencies now?", default=True
    )
    if not install_dependencies:
        click.echo("⚠ Skipping virtual environment and dependency installation.")
        return

    os.chdir(project_name)
    click.echo("⚙ Creating virtual environment (venv)...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        click.echo("✔ Virtual environment created successfully.")
    except Exception as e:
        click.echo(f"❌ Failed to create venv: {e}")
        sys.exit(1)

    venv_python = "venv\\Scripts\\python.exe" if os.name == "nt" else "venv/bin/python"
    req_file = "requirements.txt"
    if not os.path.exists(req_file):
        click.echo("⚠ requirements.txt not found, skipping dependency installation.")
        return

    click.echo("📦 Installing dependencies from requirements.txt ...")
    try:
        subprocess.run([venv_python, "-m", "pip", "install", "-r", req_file], check=True)
        click.echo("✔ Dependencies installed successfully.")
    except Exception as e:
        click.echo(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)

    click.echo("\n🎉 Project initialization complete!")
    click.echo(f"   cd {project_name}")
    if os.name == "nt":
        click.echo("   venv\\Scripts\\activate")
    else:
        click.echo("   source venv/bin/activate")
    click.echo("   pyartisan serve\n")


def dispatch_make(target: str, name: str, force: bool = False) -> None:
    """Process file generation using manifest.yaml configuration."""
    cwd = Path.cwd()
    manifest = load_manifest(cwd)

    if "generators" not in manifest or target not in manifest["generators"]:
        avail = ", ".join(manifest.get("generators", {}).keys())
        raise GeneratorNotSupported(
            f"'{manifest['id']}' does not support generator '{target}'. "
            f"Available: {avail}"
        )

    gen_config = manifest["generators"][target]
    stub_rel = gen_config.get("stub")
    path_key = gen_config.get("path")

    if not stub_rel or not path_key:
        raise ManifestError(f"Generator '{target}' configuration must specify 'stub' and 'path' keys.")

    stub_dir = cwd / ".pyartisan" / stub_rel
    if not stub_dir.exists():
        raise ManifestError(f"Stub directory not found on disk: {stub_dir}")

    dest_path_rel = manifest.get("paths", {}).get(path_key)
    if not dest_path_rel:
        raise ManifestError(f"Path key '{path_key}' (used by '{target}') is not defined in manifest 'paths'.")

    dest_dir = cwd / dest_path_rel

    # Render context
    name_lower, name_title, name_snake, name_plural = name_parts(name)
    context = {
        "name": name,
        "name_lower": name_lower,
        "name_title": name_title,
        "name_snake": name_snake,
        "name_plural": name_plural,
    }

    click.echo(f"Scaffolding '{name_title}' ({target}) ...")
    render_stub(stub_dir, dest_dir, context, force=force)

    # Registration
    if "registration" in gen_config:
        reg = gen_config["registration"]
        reg_type = reg.get("type")
        target_template = reg.get("target")

        if not reg_type or not target_template:
            raise ManifestError(f"Registration configuration for '{target}' is missing 'type' or 'target'.")

        # Render target path
        from jinja2 import Environment
        target_file_rel = Environment().from_string(target_template).render(
            path=dest_path_rel, **context
        )
        target_file = cwd / target_file_rel

        apply_registration(
            reg_type=reg_type,
            target_file=target_file,
            context=context,
            marker=reg.get("marker"),
            line_template=reg.get("line")
        )

    click.echo(f"Done. '{name_title}' scaffolded successfully.")


def _docker_available() -> bool:
    try:
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except Exception:
        return False


def dispatch_serve() -> None:
    """Run dev server using the fallback docker -> venv -> warning strategy."""
    cwd = Path.cwd()
    manifest = load_manifest(cwd)  # ensures it's a project

    # 1. Cek docker compose
    if (cwd / "docker-compose.yml").exists() and _docker_available():
        click.echo("Starting dev server with Docker (docker compose up) ...")
        try:
            cmd = ["docker", "compose", "up"]
            try:
                subprocess.run(["docker", "compose", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except Exception:
                cmd = ["docker-compose", "up"]
            subprocess.run(cmd)
        except KeyboardInterrupt:
            click.echo("\nServer stopped.")
        return

    # 2. Cek venv + script serve
    is_venv = sys.prefix != sys.base_prefix or os.environ.get("VIRTUAL_ENV") is not None
    serve_script = manifest.get("scripts", {}).get("serve")

    if is_venv and serve_script:
        click.echo("Starting dev server locally ...")
        try:
            subprocess.run(shlex.split(serve_script))
        except KeyboardInterrupt:
            click.echo("\nServer stopped.")
        except Exception as e:
            click.echo(f"❌ Serve script failed: {e}")
            sys.exit(1)
        return

    # 3. Fallback warning
    click.echo("Error: No docker-compose.yml active and no active virtual environment.")
    click.echo("  To resolve:")
    click.echo("    - Make sure Docker is running and run `pyartisan make docker` if needed.")
    if serve_script:
        click.echo("    - Activate your virtual environment first:")
        click.echo("        Mac/Linux: source venv/bin/activate")
        click.echo("        Windows:   venv\\Scripts\\activate")
    sys.exit(1)


def dispatch_build() -> None:
    """Run production build script."""
    cwd = Path.cwd()
    manifest = load_manifest(cwd)
    build_script = manifest.get("scripts", {}).get("build")

    if not build_script:
        click.echo("❌ No 'build' script defined in manifest.yaml.")
        sys.exit(1)

    click.echo(f"Running build script: {build_script} ...")
    try:
        subprocess.run(shlex.split(build_script), check=True)
        click.echo("✔ Build completed successfully.")
    except Exception as e:
        click.echo(f"❌ Build failed: {e}")
        sys.exit(1)
