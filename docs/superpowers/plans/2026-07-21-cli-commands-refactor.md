# CLI Commands Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor monolithic CLI code from `cli/__init__.py` and `marketplace/__init__.py` into a modular package structure in `src/pyartisan/cli/commands/` where each command has its own dedicated file.

**Architecture:** Create a `commands/` sub-package under `src/pyartisan/cli/`. Extract individual top-level commands (`new`, `make`, `serve`, `build`, `config`, `doctor`, `version`) and the `plugin` group command into separate files. Extract marketplace helper functions into `src/pyartisan/marketplace/core.py`. Register all commands in `src/pyartisan/cli/__init__.py`.

**Tech Stack:** Python 3.10+, Click CLI, Git, Standard Library (pathlib, shutil, subprocess, json, os).

## Global Constraints

- Preserve all existing command names, options, arguments, and help messages verbatim.
- All existing imports in `tests/smoke_test.py` must continue to work without modification (keep backward compatibility).
- Keep exact code signatures and error output formats (`❌ ...`, `✔ ...`).
- Pass `PYTHONPATH=src python3 tests/smoke_test.py` at every task completion.

---

### Task 1: Extract Marketplace Helpers to `src/pyartisan/marketplace/core.py`

**Files:**
- Create: `src/pyartisan/marketplace/core.py`
- Modify: `src/pyartisan/marketplace/__init__.py`

**Interfaces:**
- Consumes: Standard library modules, `pyartisan.core.plugin_engine.ProjectContext`, `load_plugin_yaml`
- Produces: `_global_registry`, `_plugins_registry`, `_usage_file`, `_load_usage`, `_save_usage`, `_record_usage`, `_unrecord_usage`, `_all_usages`, `_load_hooks`, `_verify_blockchain_license`, `_resolve_plugin_version`, `_find_registry_dir`, `_version_key`, `_latest_version`, `_check_updates`

- [ ] **Step 1: Create `src/pyartisan/marketplace/core.py` with helper functions**

Extract helper functions from `marketplace/__init__.py` into `marketplace/core.py`:

```python
import os
import shutil
import subprocess
import json
from pathlib import Path
import click
import yaml

from pyartisan.core.plugin_engine import ProjectContext, load_plugin_yaml


def _global_registry() -> Path:
    return Path(os.path.expanduser("~")) / ".pyartisan"


def _plugins_registry() -> Path:
    reg = _global_registry() / "plugins"
    reg.mkdir(parents=True, exist_ok=True)
    return reg


def _usage_file(plugins_registry: Path, plugin_id: str) -> Path:
    return plugins_registry / plugin_id / "usage.json"


def _load_usage(plugins_registry: Path, plugin_id: str) -> dict:
    f = _usage_file(plugins_registry, plugin_id)
    if f.exists():
        return json.loads(f.read_text())
    return {}


def _save_usage(plugins_registry: Path, plugin_id: str, data: dict) -> None:
    f = _usage_file(plugins_registry, plugin_id)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2))


def _record_usage(plugins_registry: Path, plugin_id: str, version: str, project_path: str) -> None:
    data = _load_usage(plugins_registry, plugin_id)
    projects = data.setdefault(version, [])
    if project_path not in projects:
        projects.append(project_path)
    _save_usage(plugins_registry, plugin_id, data)


def _unrecord_usage(plugins_registry: Path, plugin_id: str, version: str, project_path: str) -> None:
    data = _load_usage(plugins_registry, plugin_id)
    projects = data.get(version, [])
    if project_path in projects:
        projects.remove(project_path)
    data[version] = projects
    _save_usage(plugins_registry, plugin_id, data)


def _all_usages(plugins_registry: Path, plugin_id: str) -> list:
    data = _load_usage(plugins_registry, plugin_id)
    result = []
    for projects in data.values():
        result.extend(projects)
    return result


def _load_hooks(plugin_dir: Path):
    hooks_file = plugin_dir / "hooks.py"
    if not hooks_file.exists():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location("plugin_hooks", hooks_file)
    hooks_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hooks_module)
    return hooks_module


def _verify_blockchain_license(plugin_id: str, license_key: str) -> bool:
    if license_key.startswith("valid-"):
        return True
    return False


def _resolve_plugin_version(plugin_root: Path) -> str:
    version_dirs = sorted(d.name for d in plugin_root.iterdir() if d.is_dir())
    if "dev" in version_dirs:
        return "dev"
    if version_dirs:
        return _latest_version(version_dirs)
    return None


def _find_registry_dir(plugins_registry: Path, plugin_id: str, version: str) -> Path:
    plugin_root = plugins_registry / plugin_id
    exact = plugin_root / version if version else None
    if exact and exact.exists():
        return exact
    if (plugin_root / "dev").exists():
        return plugin_root / "dev"
    if plugin_root.exists():
        fallback_version = _resolve_plugin_version(plugin_root)
        if fallback_version:
            return plugin_root / fallback_version
    return plugin_root / (version or "dev")


def _version_key(version: str):
    return tuple(int(part) if part.isdigit() else part for part in version.split("."))


def _latest_version(versions: list) -> str:
    numeric = [v for v in versions if v != "dev"]
    if not numeric:
        return versions[-1]
    return sorted(numeric, key=_version_key)[-1]


def _check_updates():
    plugins_registry = _plugins_registry()
    found_any = False

    for plugin_root in sorted(plugins_registry.iterdir()):
        if not plugin_root.is_dir():
            continue
        for version_dir in sorted(plugin_root.iterdir()):
            if version_dir.name == "dev" or not (version_dir / ".git").exists():
                continue

            found_any = True
            try:
                local_head = subprocess.run(
                    ["git", "-C", str(version_dir), "rev-parse", "HEAD"],
                    check=True, capture_output=True, text=True
                ).stdout.strip()
                subprocess.run(
                    ["git", "-C", str(version_dir), "fetch"],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                remote_head = subprocess.run(
                    ["git", "-C", str(version_dir), "rev-parse", "@{u}"],
                    check=True, capture_output=True, text=True
                ).stdout.strip()
            except Exception:
                click.echo(f"{plugin_root.name}@{version_dir.name}: cannot check (offline or no upstream)")
                continue

            if local_head != remote_head:
                click.echo(f"{plugin_root.name}@{version_dir.name}: Update available (run `pyartisan plugin update {plugin_root.name}`)")
            else:
                click.echo(f"{plugin_root.name}@{version_dir.name}: Up to date")

    if not found_any:
        click.echo("No git-based plugins in registry to check.")
```

- [ ] **Step 2: Update `src/pyartisan/marketplace/__init__.py` to import from `marketplace.core`**

Update `src/pyartisan/marketplace/__init__.py` to import all helpers from `pyartisan.marketplace.core` and re-export them for backward compatibility.

- [ ] **Step 3: Run smoke tests to ensure no regressions**

Run: `PYTHONPATH=src python3 tests/smoke_test.py`
Expected: `ALL SMOKE TESTS PASSED`

- [ ] **Step 4: Commit**

```bash
git add src/pyartisan/marketplace/core.py src/pyartisan/marketplace/__init__.py
git commit -m "refactor: extract marketplace helper functions to marketplace.core"
```

---

### Task 2: Create `cli/commands/` Package & Individual Command Modules

**Files:**
- Create: `src/pyartisan/cli/commands/__init__.py`
- Create: `src/pyartisan/cli/commands/new.py`
- Create: `src/pyartisan/cli/commands/make.py`
- Create: `src/pyartisan/cli/commands/serve.py`
- Create: `src/pyartisan/cli/commands/build.py`
- Create: `src/pyartisan/cli/commands/config.py`
- Create: `src/pyartisan/cli/commands/doctor.py`
- Create: `src/pyartisan/cli/commands/version.py`
- Create: `src/pyartisan/cli/commands/plugin.py`

**Interfaces:**
- Consumes: `pyartisan.core.engine`, `pyartisan.config`, `pyartisan.shared.doctor`, `pyartisan.marketplace.core`
- Produces: `new_cmd`, `make_cmd`, `serve_cmd`, `build_cmd`, `config_group`, `doctor_cmd`, `version_cmd`, `plugin_group`

- [ ] **Step 1: Create `src/pyartisan/cli/commands/new.py`**

```python
import sys
import click
from pyartisan.core import engine
from pyartisan.core.exceptions import PyArtisanError


@click.command(name="new")
@click.argument("framework")
@click.argument("name")
def new_cmd(framework: str, name: str) -> None:
    """Create a new project using framework template."""
    try:
        engine.dispatch_new(framework, name)
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)
```

- [ ] **Step 2: Create `src/pyartisan/cli/commands/make.py`**

```python
import sys
import click
from pyartisan.core import engine
from pyartisan.core.exceptions import PyArtisanError


@click.command(name="make", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("target")
@click.argument("name")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing files")
@click.pass_context
def make_cmd(ctx, target: str, name: str, force: bool) -> None:
    """Scaffold files from template stubs (e.g. make controller Post)."""
    extra_options = {}
    it = iter(ctx.args)
    for item in it:
        if item.startswith("--"):
            key = item[2:].replace("-", "_")
            try:
                val = next(it)
                extra_options[key] = val
            except StopIteration:
                extra_options[key] = True
    try:
        engine.dispatch_make(target, name, force=force, **extra_options)
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)
```

- [ ] **Step 3: Create `src/pyartisan/cli/commands/serve.py`**

```python
import sys
import click
from pyartisan.core import engine
from pyartisan.core.exceptions import PyArtisanError


@click.command(name="serve")
def serve_cmd() -> None:
    """Run dev server (Docker fallback to local virtualenv)."""
    try:
        engine.dispatch_serve()
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)
```

- [ ] **Step 4: Create `src/pyartisan/cli/commands/build.py`**

```python
import sys
import click
from pyartisan.core import engine
from pyartisan.core.exceptions import PyArtisanError


@click.command(name="build")
def build_cmd() -> None:
    """Build production artifact using manifest build script."""
    try:
        engine.dispatch_build()
    except PyArtisanError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)
```

- [ ] **Step 5: Create `src/pyartisan/cli/commands/config.py`**

```python
import sys
import click
from pyartisan import config as config_module


@click.group(name="config", invoke_without_command=True)
@click.pass_context
def config_group(ctx):
    """Manage ~/.pyartisan/config.toml"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(config_show)


@config_group.command(name="show")
def config_show():
    """Print current configuration."""
    data = config_module.load()
    for key, value in data.items():
        click.echo(f"{key} = {value!r}")


@config_group.command(name="reset")
def config_reset():
    """Reset configuration to defaults."""
    config_module.reset()
    click.echo("✔ Configuration reset to defaults.")


@config_group.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a config key, e.g. pyartisan config set templates.flask <url>"""
    data = config_module.load()

    if key.startswith("templates."):
        sub = key.split(".")[1]
        if "templates" not in data:
            data["templates"] = {}
        data["templates"][sub] = value
    else:
        if key not in data:
            click.echo(f"❌ Unknown config key: {key}")
            sys.exit(1)
        data[key] = value

    config_module.save(data)
    click.echo(f"✔ {key} = {value}")
```

- [ ] **Step 6: Create `src/pyartisan/cli/commands/doctor.py`**

```python
import sys
import click
from pyartisan.shared.doctor import run_checks


@click.command(name="doctor")
def doctor_cmd() -> None:
    """Check Python, pip, Git, and environment health."""
    ok = run_checks()
    if not ok:
        sys.exit(1)
```

- [ ] **Step 7: Create `src/pyartisan/cli/commands/version.py`**

```python
import click
from pyartisan import __version__


@click.command(name="version")
def version_cmd() -> None:
    """Show pyartisan version."""
    click.echo(f"pyartisan {__version__}")
```

- [ ] **Step 8: Move `plugin_group` from `marketplace/__init__.py` to `src/pyartisan/cli/commands/plugin.py`**

Move the `@click.group(name="plugin")` and all its subcommand functions (`install_cmd`, `apply_cmd`, `update_cmd`, `remove_cmd`, `uninstall_cmd`, `list_cmd`, `info_cmd`, `status_cmd`, `doctor_cmd`, `init_cmd`) from `marketplace/__init__.py` to `src/pyartisan/cli/commands/plugin.py`, importing helper functions from `pyartisan.marketplace.core`.

- [ ] **Step 9: Create `src/pyartisan/cli/commands/__init__.py` to export all commands**

```python
from pyartisan.cli.commands.new import new_cmd
from pyartisan.cli.commands.make import make_cmd
from pyartisan.cli.commands.serve import serve_cmd
from pyartisan.cli.commands.build import build_cmd
from pyartisan.cli.commands.config import config_group
from pyartisan.cli.commands.doctor import doctor_cmd
from pyartisan.cli.commands.version import version_cmd
from pyartisan.cli.commands.plugin import plugin_group

__all__ = [
    "new_cmd",
    "make_cmd",
    "serve_cmd",
    "build_cmd",
    "config_group",
    "doctor_cmd",
    "version_cmd",
    "plugin_group",
]
```

- [ ] **Step 10: Commit task files**

```bash
git add src/pyartisan/cli/commands/
git commit -m "feat: add individual command modules under cli/commands/"
```

---

### Task 3: Refactor `src/pyartisan/cli/__init__.py` and `src/pyartisan/marketplace/__init__.py`

**Files:**
- Modify: `src/pyartisan/cli/__init__.py`
- Modify: `src/pyartisan/marketplace/__init__.py`

**Interfaces:**
- Consumes: `src/pyartisan/cli/commands/*`
- Produces: CLI entrypoint (`cli`), backward-compatible `plugin_group` export in `marketplace`

- [ ] **Step 1: Update `src/pyartisan/cli/__init__.py`**

Refactor `src/pyartisan/cli/__init__.py` to register all commands from `cli.commands`:

```python
import click
from pyartisan import __version__
from pyartisan.cli.commands import (
    new_cmd,
    make_cmd,
    serve_cmd,
    build_cmd,
    config_group,
    doctor_cmd,
    version_cmd,
    plugin_group,
)


@click.group()
@click.version_option(__version__, prog_name="pyartisan")
def cli():
    """pyartisan - AI-powered Python Web Development Toolkit"""
    pass


cli.add_command(new_cmd)
cli.add_command(make_cmd)
cli.add_command(serve_cmd)
cli.add_command(build_cmd)
cli.add_command(config_group)
cli.add_command(doctor_cmd)
cli.add_command(version_cmd)
cli.add_command(plugin_group)


if __name__ == "__main__":
    cli()
```

- [ ] **Step 2: Update `src/pyartisan/marketplace/__init__.py` for backward compatibility**

Keep `marketplace/__init__.py` thin, re-exporting `plugin_group` from `pyartisan.cli.commands.plugin` and all helpers from `pyartisan.marketplace.core` so existing imports remain intact:

```python
from pyartisan.cli.commands.plugin import plugin_group
from pyartisan.marketplace.core import *

__all__ = ["plugin_group"]
```

- [ ] **Step 3: Run smoke tests to verify all tests pass**

Run: `PYTHONPATH=src python3 tests/smoke_test.py`
Expected: `ALL SMOKE TESTS PASSED`

- [ ] **Step 4: Manual CLI check**

Run: `python3 -m pyartisan.cli --help`
Expected: Show all commands (`new`, `make`, `serve`, `build`, `config`, `doctor`, `version`, `plugin`).

- [ ] **Step 5: Commit**

```bash
git add src/pyartisan/cli/__init__.py src/pyartisan/marketplace/__init__.py
git commit -m "refactor: register CLI commands from cli.commands package"
```
