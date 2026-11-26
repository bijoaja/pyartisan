import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import click
import yaml

from pyartisan import config as config_module
from pyartisan.core.exceptions import (
    GeneratorNotSupported,
    ManifestError,
    PyArtisanError,
    ServeError,
    TemplateNotFound,
)
from pyartisan.core.manifest import load_manifest
from pyartisan.core.registration import apply_registration
from pyartisan.renderer import make_env, render_stub
from pyartisan.utils.naming import name_parts
from pyartisan.utils.safe import safe_child, validate_clone_url, validate_name


def _venv_cmd(uv: str | None) -> list[str]:
    return [uv, "venv", "venv"] if uv else [sys.executable, "-m", "venv", "venv"]


def _install_cmd(uv: str | None, venv_python: str, req_file: str) -> list[str]:
    if uv:
        return [uv, "pip", "install", "--python", venv_python, "-r", req_file]
    return [venv_python, "-m", "pip", "install", "-r", req_file]


def _detect_install_plan(
    cwd: Path, uv: str | None, venv_python: str
) -> tuple[str, list[str]] | None:
    """Return (description, command) for installing project dependencies, or None."""
    pyproject = cwd / "pyproject.toml"
    req_file = cwd / "requirements.txt"

    if pyproject.exists():
        if uv:
            return "dependencies via uv sync", [uv, "sync"]
        return "project dependencies via pip (pyproject.toml)", [
            venv_python,
            "-m",
            "pip",
            "install",
            "-e",
            ".",
        ]

    if req_file.exists():
        return "dependencies from requirements.txt", _install_cmd(
            uv, venv_python, str(req_file.name)
        )

    return None


def _template_meta(manifest_path: Path, default_name: str, default_version: str) -> tuple[str, str]:
    if not manifest_path.exists():
        return default_name, default_version
    try:
        with open(manifest_path, encoding="utf-8") as f:
            m_data = yaml.safe_load(f)
        if not isinstance(m_data, dict):
            click.echo(
                f"⚠ Could not read template manifest: expected mapping, got {type(m_data).__name__}. Using defaults."
            )
            return default_name, default_version
        tid = m_data.get("id")
        tver = m_data.get("version")
        template_name = str(tid) if tid is not None else default_name
        template_version = str(tver) if tver is not None else default_version
        return template_name, template_version
    except (OSError, yaml.YAMLError) as e:
        click.echo(f"⚠ Could not read template manifest: {e}. Using defaults.")
        return default_name, default_version


def dispatch_new(framework: str, project_name: str) -> None:
    """Initialize a new project by cloning the framework template."""
    validate_name(project_name, "project name")
    config_data = config_module.load()
    templates = config_data.get(
        "templates",
        {
            "flask": "https://github.com/bijoaja/flaskiq.git",
            "fastapi": "https://github.com/bijoaja/fastiq.git",
        },
    )

    if framework not in templates:
        raise TemplateNotFound(
            f"No template registered for framework '{framework}'. "
            f"Available: {', '.join(templates.keys())}"
        )

    repo_url = templates[framework]
    validate_clone_url(repo_url, "template URL")

    if os.path.exists(project_name):
        click.echo(f"❌ Folder '{project_name}' already exists, choose a different name.")
        sys.exit(1)

    click.echo(f"⬇ Cloning {framework} template repository ...")
    try:
        result = subprocess.run(
            ["git", "clone", "--", repo_url, project_name], capture_output=True, text=True
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
    template_name, template_version = _template_meta(manifest_path, framework + "iq", "1.0")

    project_yaml = {
        "project": {"name": project_name},
        "framework": {"name": framework},
        "template": {"name": template_name, "version": template_version},
        "plugins": [],
    }
    with open(Path(project_name) / ".pyartisan" / "project.yaml", "w", encoding="utf-8") as f:
        yaml.dump(project_yaml, f)

    install_dependencies = click.confirm(
        "Do you want to create a virtual environment and install dependencies now?", default=True
    )
    if not install_dependencies:
        click.echo("⚠ Skipping virtual environment and dependency installation.")
        return

    uv = shutil.which("uv")
    click.echo(f"⚙ Creating virtual environment (venv{' via uv' if uv else ''})...")
    try:
        subprocess.run(_venv_cmd(uv), cwd=project_name, check=True)
        click.echo("✔ Virtual environment created successfully.")
    except Exception as e:
        click.echo(f"❌ Failed to create venv: {e}")
        sys.exit(1)

    venv_python = "venv\\Scripts\\python.exe" if os.name == "nt" else "venv/bin/python"
    plan = _detect_install_plan(Path(project_name), uv, venv_python)
    if not plan:
        click.echo(
            "⚠ No pyproject.toml or requirements.txt found, skipping dependency installation."
        )
        return

    desc, cmd = plan
    click.echo(f"📦 Installing {desc} ...")
    try:
        subprocess.run(cmd, cwd=project_name, check=True)
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


def dispatch_make(target: str, name: str, force: bool = False, **extra_options: Any) -> None:
    """Process file generation using manifest.yaml configuration."""
    validate_name(name, "name")
    cwd = Path.cwd()
    manifest = load_manifest(cwd)

    if "generators" not in manifest or target not in manifest["generators"]:
        avail = ", ".join(manifest.get("generators", {}).keys())
        raise GeneratorNotSupported(
            f"'{manifest['id']}' does not support generator '{target}'. Available: {avail}"
        )

    gen_config = manifest["generators"][target]
    stub_rel = gen_config.get("stub")
    path_key = gen_config.get("path")

    if not stub_rel or not path_key:
        raise ManifestError(
            f"Generator '{target}' configuration must specify 'stub' and 'path' keys."
        )

    stub_dir = safe_child(cwd, ".pyartisan", stub_rel)

    dest_path_rel = manifest.get("paths", {}).get(path_key)
    if not dest_path_rel:
        raise ManifestError(
            f"Path key '{path_key}' (used by '{target}') is not defined in manifest 'paths'."
        )

    dest_dir = safe_child(cwd, dest_path_rel)

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
        **extra_options,
    }

    # Evaluate dynamic stub_subpath if defined
    if "stub_subpath" in gen_config:
        subpath_template = gen_config["stub_subpath"]
        rendered_subpath = make_env().from_string(subpath_template).render(context)
        stub_dir = safe_child(stub_dir, rendered_subpath)

    if not stub_dir.exists():
        raise ManifestError(f"Stub directory not found on disk: {stub_dir}")

    # Evaluate dynamic dest if defined
    if "dest" in gen_config:
        dest_template = gen_config["dest"]
        rendered_dest = make_env().from_string(dest_template).render(context)
        if rendered_dest:
            dest_dir = safe_child(dest_dir, rendered_dest)

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
                raise ManifestError(
                    f"Registration configuration for '{target}' is missing 'type' or 'target'."
                )

            # Render target path
            target_file_rel = (
                make_env().from_string(target_template).render(path=dest_path_rel, **context)
            )
            target_file = safe_child(cwd, target_file_rel)

            apply_registration(
                reg_type=reg_type,
                target_file=target_file,
                context=context,
                marker=reg.get("marker"),
                line_template=reg.get("line"),
            )

    click.echo(f"Done. '{name_title}' scaffolded successfully.")


def _docker_available() -> bool:
    try:
        subprocess.run(
            ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
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
        env_venv = Path(os.environ["VIRTUAL_ENV"])
        try:
            if env_venv.resolve().is_relative_to(cwd.resolve()):
                candidates.append(env_venv)
        except (ValueError, OSError):
            pass
    for c in candidates:
        if (c / "pyvenv.cfg").exists() and _venv_python(c).exists() and c.resolve() != own:
            return c
    return None


def _venv_command(venv: Path, argv: list[str]) -> tuple[list[str], dict[str, str]]:
    """Run argv inside venv. PATH alone is not trusted: on Windows `python3` does not exist in a
    venv and a PATH entry does not override the caller's own Python, so resolve argv[0] explicitly."""
    bin_dir = str(_venv_bin(venv))
    env = {
        **os.environ,
        "VIRTUAL_ENV": str(venv),
        "PATH": bin_dir + os.pathsep + os.environ.get("PATH", ""),
    }
    env.pop("PYTHONHOME", None)
    if argv[0] in ("python", "python3"):
        argv = [str(_venv_python(venv)), *argv[1:]]
    else:
        argv = [shutil.which(argv[0], path=bin_dir) or argv[0], *argv[1:]]
    return argv, env


def select_serve_mode(cwd: Path, manifest: dict[str, Any], forced: str | None = None) -> str:
    """Select execution mode ('docker', 'venv', 'uv') for dev server."""
    scripts = manifest.get("scripts") or {}
    serve = scripts.get("serve") or ""
    serve_uv = scripts.get("serve_uv") or ""
    has_uv_cmd = serve.startswith(("uv run ", "uv ")) or bool(serve_uv)

    if forced:
        if forced == "docker":
            if not ((cwd / "docker-compose.yml").exists() and _docker_available()):
                raise ServeError(
                    "Docker mode requested, but docker-compose.yml is missing or Docker daemon is not running."
                )
            return "docker"
        if forced == "venv":
            if not (_find_project_venv(cwd) is not None and bool(serve)):
                raise ServeError(
                    "Venv mode requested, but no virtual environment or serve script found."
                )
            return "venv"
        if forced == "uv":
            if not shutil.which("uv"):
                raise ServeError("Uv mode requested, but 'uv' was not found on PATH.")
            if not has_uv_cmd:
                raise ServeError(
                    "Uv mode requested, but no 'serve_uv' script defined in manifest.yaml."
                )
            return "uv"
        raise ServeError(f"Unknown serve mode: {forced}")

    # Auto fallback: docker -> venv -> uv
    if (cwd / "docker-compose.yml").exists() and _docker_available():
        return "docker"
    if _find_project_venv(cwd) is not None and bool(serve):
        return "venv"
    if shutil.which("uv") and has_uv_cmd:
        return "uv"

    lines = [
        "No docker-compose.yml active and no project virtual environment found.",
        "  To resolve:",
        "    - Make sure Docker is running and run `pyartisan make docker` if needed.",
    ]
    if serve:
        lines.append(
            "    - Create the project venv (./venv or ./.venv), e.g. `uv venv venv` and install requirements."
        )
    raise ServeError("\n".join(lines))


def _run_docker() -> None:
    click.echo("Starting dev server with Docker (docker compose up) ...")
    cmd = ["docker", "compose", "up"]
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except Exception:
        if not shutil.which("docker-compose"):
            raise ServeError(
                "Docker mode requested, but neither the Compose plugin nor docker-compose is installed."
            )
        cmd = ["docker-compose", "up"]

    try:
        res = subprocess.run(cmd)
        if res.returncode != 0:
            sys.exit(res.returncode)
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")


def _run_venv(cwd: Path, manifest: dict[str, Any]) -> None:
    venv = _find_project_venv(cwd)
    serve_script = (manifest.get("scripts") or {}).get("serve")
    if not venv or not serve_script:
        raise ServeError("Venv mode requested, but no virtual environment or serve script found.")
    click.echo(f"Starting dev server locally (venv: {venv.name}) ...")
    try:
        argv, env = _venv_command(venv, shlex.split(serve_script))
        res = subprocess.run(
            argv,
            env=env,
        )  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit - argv list from the project's own manifest, shell=False
        if res.returncode != 0:
            sys.exit(res.returncode)
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")
    except Exception as e:
        click.echo(f"❌ Serve script failed: {e}")
        sys.exit(1)


def _run_uv(manifest: dict[str, Any]) -> None:
    scripts = manifest.get("scripts") or {}
    serve = scripts.get("serve") or ""
    if serve.startswith(("uv run ", "uv ")):
        uv_cmd = serve
    else:
        uv_cmd = scripts.get("serve_uv") or ""
    if not uv_cmd:
        raise ServeError("Uv mode requested, but no 'serve_uv' script defined in manifest.yaml.")
    click.echo(f"Starting dev server with uv ({uv_cmd}) ...")
    try:
        res = subprocess.run(
            shlex.split(uv_cmd)
        )  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit - argv list from the project's own manifest, shell=False
        if res.returncode != 0:
            sys.exit(res.returncode)
    except KeyboardInterrupt:
        click.echo("\nServer stopped.")
    except Exception as e:
        click.echo(f"❌ Serve script failed: {e}")
        sys.exit(1)


def dispatch_serve(mode: str | None = None) -> None:
    """Run dev server using the fallback docker -> venv -> uv strategy or forced mode."""
    cwd = Path.cwd()
    manifest = load_manifest(cwd)  # ensures it's a project
    selected = select_serve_mode(cwd, manifest, forced=mode)

    if selected == "docker":
        _run_docker()
    elif selected == "venv":
        _run_venv(cwd, manifest)
    elif selected == "uv":
        _run_uv(manifest)


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


def analyze_steps(
    manifest: dict[str, Any], fix: bool = False, cwd: Path | None = None
) -> list[tuple[str, str]]:
    """Determine analysis steps from manifest or fallback defaults."""
    scripts = manifest.get("scripts")
    if not isinstance(scripts, dict):
        scripts = {}

    if "analyze" in scripts and scripts["analyze"] is not None:
        analyze_cfg = scripts["analyze"]
        if not isinstance(analyze_cfg, list):
            raise ManifestError(
                "scripts.analyze must be a list of step mappings, got "
                f"{type(analyze_cfg).__name__}."
            )
        if analyze_cfg:
            steps: list[tuple[str, str]] = []
            for i, step in enumerate(analyze_cfg):
                if (
                    not isinstance(step, dict)
                    or not isinstance(step.get("name"), str)
                    or not isinstance(step.get("cmd"), str)
                ):
                    raise ManifestError(
                        f"Invalid scripts.analyze[{i}]: expected mapping with string 'name' and 'cmd'."
                    )
                name = step["name"]
                cmd = str(step.get("fix") if fix and "fix" in step else step["cmd"])
                steps.append((name, cmd))
            return steps

    target_cwd = cwd or Path.cwd()
    targets = [d for d in ("src", "app") if (target_cwd / d).is_dir()]
    bandit_target = " ".join(targets) if targets else "."

    return [
        ("ruff-check", "ruff check --fix ." if fix else "ruff check ."),
        ("ruff-format", "ruff format ." if fix else "ruff format --check ."),
        ("bandit", f"bandit -q -r {bandit_target} -c pyproject.toml"),
        ("mypy", "mypy ."),
    ]


def dispatch_analyze(
    only: tuple[str, ...] = (),
    fix: bool = False,
    cwd: Path | None = None,
) -> None:
    """Run code quality and security checks."""
    target_cwd = cwd or Path.cwd()
    manifest = load_manifest(target_cwd)
    steps = analyze_steps(manifest, fix=fix, cwd=target_cwd)

    if only:
        valid_names = [s[0] for s in steps]
        for name in only:
            if name not in valid_names:
                raise PyArtisanError(
                    f"Unknown check '{name}'. Available checks: {', '.join(valid_names)}"
                )
        steps = [s for s in steps if s[0] in only]

    if not steps:
        raise PyArtisanError("No checks to run.")

    venv = _find_project_venv(target_cwd)
    failed: list[str] = []

    for name, cmd_str in steps:
        click.echo(f"Running {name} ({cmd_str}) ...")
        argv = shlex.split(cmd_str)
        if not argv:
            failed.append(name)
            click.echo(f"❌ {name} failed: empty command.")
            continue

        if argv[0] == "uv":
            if not shutil.which("uv"):
                failed.append(name)
                click.echo(f"❌ {name} failed: 'uv' not found on PATH.")
                continue
            cmd_argv, env = argv, os.environ.copy()
        elif venv is not None:
            bin_dir = str(_venv_bin(venv))
            tool = argv[0]
            if tool not in ("python", "python3") and not shutil.which(tool, path=bin_dir):
                failed.append(name)
                click.echo(f"❌ {name} failed: tool '{tool}' not found in project venv.")
                continue
            cmd_argv, env = _venv_command(venv, argv)
        else:
            cmd_argv, env = argv, os.environ.copy()

        try:
            result = subprocess.run(
                cmd_argv,
                env=env,
                cwd=target_cwd,
            )  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit - argv list from the project's own manifest, shell=False
            if result.returncode == 0:
                click.echo(f"✔ {name} passed.")
            else:
                failed.append(name)
                click.echo(f"❌ {name} failed.")
        except FileNotFoundError:
            failed.append(name)
            tool_name = argv[0] if argv else cmd_str
            click.echo(f"❌ {name} failed: tool '{tool_name}' not found.")
        except Exception as e:
            failed.append(name)
            click.echo(f"❌ {name} failed: {e}")

    if failed:
        click.echo(f"Some checks failed: {', '.join(failed)}.")
        sys.exit(1)

    click.echo("All checks passed.")
