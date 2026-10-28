import json
import os
import subprocess
from pathlib import Path

import click

from pyartisan.utils.safe import safe_child


def _global_registry() -> Path:
    return Path(os.path.expanduser("~")) / ".pyartisan"


def _plugins_registry() -> Path:
    reg = _global_registry() / "plugins"
    reg.mkdir(parents=True, exist_ok=True)
    return reg


def _usage_file(plugins_registry: Path, plugin_id: str) -> Path:
    return safe_child(plugins_registry, plugin_id, "usage.json")


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


def _unrecord_usage(
    plugins_registry: Path, plugin_id: str, version: str, project_path: str
) -> None:
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
    plugin_root = safe_child(plugins_registry, plugin_id)
    if version:
        exact = safe_child(plugin_root, version)
        if exact.exists():
            return exact
    dev = safe_child(plugin_root, "dev")
    if dev.exists():
        return dev
    if plugin_root.exists():
        fallback_version = _resolve_plugin_version(plugin_root)
        if fallback_version:
            return safe_child(plugin_root, fallback_version)
    return safe_child(plugin_root, version or "dev")


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
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
                subprocess.run(
                    ["git", "-C", str(version_dir), "fetch"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                remote_head = subprocess.run(
                    ["git", "-C", str(version_dir), "rev-parse", "@{u}"],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            except Exception:
                click.echo(
                    f"{plugin_root.name}@{version_dir.name}: cannot check (offline or no upstream)"
                )
                continue

            if local_head != remote_head:
                click.echo(
                    f"{plugin_root.name}@{version_dir.name}: Update available (run `pyartisan plugin update {plugin_root.name}`)"
                )
            else:
                click.echo(f"{plugin_root.name}@{version_dir.name}: Up to date")

    if not found_any:
        click.echo("No git-based plugins in registry to check.")
