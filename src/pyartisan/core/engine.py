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
import yaml


def _venv_cmd(uv: str | None) -> list[str]:
    return [uv, "venv", "venv"] if uv else [sys.executable, "-m", "venv", "venv"]


def _install_cmd(uv: str | None, venv_python: str, req_file: str) -> list[str]:
    if uv:
        return [uv, "pip", "install", "--python", venv_python, "-r", req_file]
    return [venv_python, "-m", "pip", "install", "-r", req_file]


def _detect_install_plan(cwd: Path, uv: str | None, venv_python: str) -> tuple[str, list[str]] | None:
    """Return (description, command) for installing project dependencies, or None."""
    pyproject = cwd / "pyproject.toml"
    req_file = cwd / "requirements.txt"

    if pyproject.exists():
        if uv:
            return "dependencies via uv sync", [uv, "sync"]
        return "project dependencies via pip (pyproject.toml)", [venv_python, "-m", "pip", "install", "-e", "."]

    if req_file.exists():
        return "dependencies from requirements.txt", _install_cmd(uv, venv_python, str(req_file.name))

    return None


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

    # Generate .pyartisan/project.yaml (baca manifest.yaml di dalam template)
    manifest_path = Path(project_name) / ".pyartisan" / "manifest.yaml"
    template_name = framework + "iq"
    template_version = "1.0"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r") as f:
                m_data = yaml.safe_load(f)
                template_name = m_data.get("id", template_name)
                template_version = str(m_data.get("version", template_version))
        except Exception:
            pass

    project_yaml = {
        "project": {"name": project_name},
        "framework": {"name": framework},
        "template": {
            "name": template_name,
            "version": template_version
        },
        "plugins": []
    }
    with open(Path(project_name) / ".pyartisan" / "project.yaml", "w") as f:
        yaml.dump(project_yaml, f)

    install_dependencies = click.confirm(
        "Do you want to create a virtual environment and install dependencies now?", default=True
    )
    if not install_dependencies:
        click.echo("⚠ Skipping virtual environment and dependency installation.")
        return

    os.chdir(project_name)
    uv = shutil.which("uv")
    click.echo(f"⚙ Creating virtual environment (venv{' via uv' if uv else ''})...")
    try:
        subprocess.run(_venv_cmd(uv), check=True)
        click.echo("✔ Virtual environment created successfully.")
    except Exception as e:
        click.echo(f"❌ Failed to create venv: {e}")
        sys.exit(1)

    venv_python = "venv\\Scripts\\python.exe" if os.name == "nt" else "venv/bin/python"
    plan = _detect_install_plan(Path.cwd(), uv, venv_python)
    if not plan:
        click.echo("⚠ No pyproject.toml or requirements.txt found, skipping dependency installation.")
        return

    desc, cmd = plan
    click.echo(f"📦 Installing {desc} ...")
    try:
        subprocess.run(cmd, check=True)
        click.echo("✔ Dependencies installed successfully.")
    except Exception as e:
        click.echo(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)

    click.echo("\n🎉 Project initialization complete!")
    if os.name == "nt":
        click.echo("   venv\\Scripts\\activate")
    else:
        click.echo("   source venv/bin/activate")
    click.echo("   pyartisan serve\n")


def dispatch_make(target: str, name: str, force: bool = False, **extra_options) -> None:
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
        "type": extra_options.get("type", "view"),
        "version": extra_options.get("version", "1"),
        **extra_options
    }

    # Evaluate dynamic stub_subpath if defined
    from jinja2 import Environment
    if "stub_subpath" in gen_config:
        subpath_template = gen_config["stub_subpath"]
        rendered_subpath = Environment().from_string(subpath_template).render(context)
        stub_dir = stub_dir / rendered_subpath

    if not stub_dir.exists():
        raise ManifestError(f"Stub directory not found on disk: {stub_dir}")

    # Evaluate dynamic dest if defined
    if "dest" in gen_config:
        dest_template = gen_config["dest"]
        rendered_dest = Environment().from_string(dest_template).render(context)
        dest_dir = dest_dir / rendered_dest

    click.echo(f"Scaffolding '{name_title}' ({target}) ...")
    render_stub(stub_dir, dest_dir, context, force=force)

    # Registration
    if "registration" in gen_config:
        registrations = gen_config["registration"]
        # Normalize to list of dicts for dynamic support (backward compatible)
        if isinstance(registrations, dict):
            registrations = [registrations]

        for reg in registrations:
            reg_type = reg.get("type")
            target_template = reg.get("target")

            if not reg_type or not target_template:
                raise ManifestError(f"Registration configuration for '{target}' is missing 'type' or 'target'.")

            # Render target path
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


def _venv_bin(venv: Path) -> Path:
    return venv / ("Scripts" if os.name == "nt" else "bin")


def _venv_python(venv: Path) -> Path:
    return _venv_bin(venv) / ("python.exe" if os.name == "nt" else "python")


def _find_project_venv(cwd: Path) -> Path | None:
    """Venv of the project, never the env pyartisan itself runs in (e.g. a `uv tool` env)."""
    own = Path(sys.prefix).resolve()
    candidates = [cwd / "venv", cwd / ".venv"]
    if os.environ.get("VIRTUAL_ENV"):
        candidates.append(Path(os.environ["VIRTUAL_ENV"]))
    for c in candidates:
        if (c / "pyvenv.cfg").exists() and _venv_python(c).exists() and c.resolve() != own:
            return c
    return None


def _venv_command(venv: Path, argv: list[str]) -> tuple[list[str], dict]:
    """Run argv inside venv. PATH alone is not trusted: on Windows `python3` does not exist in a
    venv and a PATH entry does not override the caller's own Python, so resolve argv[0] explicitly."""
    bin_dir = str(_venv_bin(venv))
    env = {**os.environ, "VIRTUAL_ENV": str(venv), "PATH": bin_dir + os.pathsep + os.environ.get("PATH", "")}
    env.pop("PYTHONHOME", None)
    if argv[0] in ("python", "python3"):
        argv = [str(_venv_python(venv)), *argv[1:]]
    else:
        argv = [shutil.which(argv[0], path=env["PATH"]) or argv[0], *argv[1:]]
    return argv, env


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
    venv = _find_project_venv(cwd)
    serve_script = manifest.get("scripts", {}).get("serve")

    if venv and serve_script:
        click.echo(f"Starting dev server locally (venv: {venv.name}) ...")
        try:
            argv, env = _venv_command(venv, shlex.split(serve_script))
            subprocess.run(argv, env=env)
        except KeyboardInterrupt:
            click.echo("\nServer stopped.")
        except Exception as e:
            click.echo(f"❌ Serve script failed: {e}")
            sys.exit(1)
        return

    # 3. Fallback warning
    click.echo("Error: No docker-compose.yml active and no project virtual environment found.")
    click.echo("  To resolve:")
    click.echo("    - Make sure Docker is running and run `pyartisan make docker` if needed.")
    if serve_script:
        click.echo("    - Create the project venv (./venv or ./.venv), e.g. `uv venv venv` and install requirements.")
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
