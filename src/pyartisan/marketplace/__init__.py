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
    """Mock verification of blockchain license credential signature."""
    # Menghubungi node / API gateway blockchain mock.
    # Untuk uji coba/demo, jika license_key valid (misal diawali 'valid-'), return True.
    if license_key.startswith("valid-"):
        return True
    return False


@click.group(name="plugin")
def plugin_group():
    """Manage PyArtisan plugins (community & marketplace)"""
    pass


@plugin_group.command(name="install")
@click.argument("name")
@click.option("--local", type=str, help="Install plugin from local directory path")
@click.option("--license", type=str, help="License key for premium marketplace plugins")
def install_cmd(name: str, local: str, license: str):
    """Download plugin into the global registry (does not affect any project)."""
    plugins_registry = _plugins_registry()
    plugin_dir = None

    if local:
        local_path = Path(local)
        if not local_path.exists():
            click.echo(f"❌ Local path does not exist: {local}")
            return

        plugin_dir = plugins_registry / name / "dev"
        plugin_dir.parent.mkdir(parents=True, exist_ok=True)
        if plugin_dir.exists() or plugin_dir.is_symlink():
            if plugin_dir.is_symlink():
                os.unlink(plugin_dir)
            else:
                shutil.rmtree(plugin_dir)

        # Gunakan symlink untuk mode pengembangan
        os.symlink(local_path.resolve(), plugin_dir, target_is_directory=True)
        click.echo(f"✔ Linked local plugin {name} -> {local_path}")
    elif license:
        click.echo("🔗 Verifying license credentials on Blockchain API node...")
        if not _verify_blockchain_license(name, license):
            click.echo("❌ Invalid license key or ownership validation failed on blockchain.")
            return
        click.echo("✔ License ownership successfully verified via Smart Contract.")
        # Mock secure download tarball premium plugin
        plugin_dir = plugins_registry / name / "1.0.0"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        manifest_data = {
            "id": name,
            "name": f"Premium {name}",
            "version": "1.0.0",
            "dependencies": {"pip": ["stripe"]}
        }
        with open(plugin_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest_data, f)
    else:
        # Komunitas (GitHub / Git URL). Format name: github-user/repo-name
        if "/" not in name:
            click.echo("❌ For community plugins, specify GitHub path 'github-username/repo-name'")
            return

        repo_url = f"https://github.com/{name}.git"
        plugin_id = name.split("/")[-1]
        plugin_dir = plugins_registry / plugin_id / "1.0.0"

        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)

        click.echo(f"⬇ Cloning plugin from {repo_url}...")
        try:
            subprocess.run(
                ["git", "clone", repo_url, str(plugin_dir)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            click.echo(f"❌ Failed to clone plugin repository: {e}")
            return

    manifest_file = plugin_dir / "manifest.yaml"
    if not manifest_file.exists():
        click.echo("❌ Plugin is missing manifest.yaml.")
        return

    plugin_manifest = load_plugin_yaml(manifest_file)
    click.echo(f"📦 Plugin '{plugin_manifest.get('name', name)}' downloaded to registry.")
    click.echo(f"👉 Run `pyartisan plugin apply {plugin_manifest['id']}` inside a project to use it.")


@plugin_group.command(name="apply")
@click.argument("name")
def apply_cmd(name: str):
    """Apply a registry-installed plugin to the current project."""
    cwd = Path.cwd()
    project_yaml_file = cwd / ".pyartisan" / "project.yaml"
    if not project_yaml_file.exists():
        click.echo("❌ Error: Not a pyartisan project. Missing .pyartisan/project.yaml.")
        return

    plugins_registry = _plugins_registry()
    plugin_root = plugins_registry / name
    if not plugin_root.exists():
        click.echo(f"❌ Plugin '{name}' not found in registry. Run `pyartisan plugin install {name}` first.")
        return

    # Versi 'dev' (symlink lokal) diprioritaskan; jika tidak, pilih versi terbaru.
    version_dirs = sorted(d.name for d in plugin_root.iterdir() if d.is_dir())
    if "dev" in version_dirs:
        version = "dev"
    elif version_dirs:
        version = version_dirs[-1]
    else:
        click.echo(f"❌ No installed version found for plugin '{name}'.")
        return

    plugin_dir = plugin_root / version
    manifest_file = plugin_dir / "manifest.yaml"
    if not manifest_file.exists():
        click.echo("❌ Plugin is missing manifest.yaml.")
        return

    plugin_manifest = load_plugin_yaml(manifest_file)
    project_ctx = ProjectContext(cwd)

    click.echo(f"📦 Applying plugin: {plugin_manifest.get('name', name)} ...")

    hooks_module = _load_hooks(plugin_dir)
    if hooks_module and hasattr(hooks_module, "before_install"):
        click.echo("🏃 Running before_install hook...")
        hooks_module.before_install(project_ctx)

    deps = plugin_manifest.get("dependencies", {})
    if deps and "pip" in deps:
        for pip_dep in deps["pip"]:
            click.echo(f"➕ Adding dependency: {pip_dep}")
            project_ctx.add_dependency(pip_dep)

    if hooks_module and hasattr(hooks_module, "after_install"):
        click.echo("🏃 Running after_install hook...")
        hooks_module.after_install(project_ctx)

    project_config = project_ctx.project_config
    if "plugins" not in project_config:
        project_config["plugins"] = []

    plugin_version = plugin_manifest.get("version", version)
    plugin_entry = f"{plugin_manifest['id']}@{plugin_version}"
    if plugin_entry not in project_config["plugins"]:
        project_config["plugins"].append(plugin_entry)
        with open(project_yaml_file, "w") as f:
            yaml.dump(project_config, f)

    _record_usage(plugins_registry, plugin_manifest["id"], plugin_version, str(cwd))

    click.echo(f"🎉 Plugin '{plugin_manifest.get('name')}' successfully applied to project!")


@plugin_group.command(name="update")
@click.argument("name")
def update_cmd(name: str):
    """Update a registry plugin's git sources and re-apply if used by current project."""
    plugins_registry = _plugins_registry()
    plugin_root = plugins_registry / name
    if not plugin_root.exists():
        click.echo(f"❌ Plugin '{name}' not found in registry.")
        return

    version_dirs = [d for d in plugin_root.iterdir() if d.is_dir()]
    if not version_dirs:
        click.echo(f"❌ No installed version found for plugin '{name}'.")
        return

    updated_any = False
    for version_dir in version_dirs:
        if version_dir.name == "dev":
            click.echo("ℹ Skipping local dev link (already live from source path).")
            continue
        if (version_dir / ".git").exists():
            click.echo(f"⬆ Pulling latest changes for {name}@{version_dir.name}...")
            try:
                subprocess.run(
                    ["git", "-C", str(version_dir), "pull"],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                updated_any = True
            except Exception as e:
                click.echo(f"❌ Failed to update {version_dir.name}: {e}")

    if not updated_any:
        click.echo("No updatable plugin sources found (only local dev links present).")
        return

    click.echo(f"✔ Plugin '{name}' updated in registry.")

    cwd = Path.cwd()
    project_yaml_file = cwd / ".pyartisan" / "project.yaml"
    if project_yaml_file.exists():
        project_config = load_plugin_yaml(project_yaml_file)
        if any(p.split("@")[0] == name for p in project_config.get("plugins", [])):
            click.echo("🔄 Re-applying updated plugin to current project...")
            ctx = click.get_current_context()
            ctx.invoke(apply_cmd, name=name)


@plugin_group.command(name="remove")
@click.argument("names", nargs=-1)
@click.option("--all", "remove_all", is_flag=True, help="Remove all plugins from project")
def remove_cmd(names, remove_all):
    """Remove plugin(s) from the current project (registry copy stays intact)."""
    cwd = Path.cwd()
    project_yaml_file = cwd / ".pyartisan" / "project.yaml"
    if not project_yaml_file.exists():
        click.echo("❌ Error: Not a pyartisan project.")
        return

    project_config = load_plugin_yaml(project_yaml_file)
    installed_plugins = project_config.get("plugins", [])

    if remove_all:
        to_remove = list(installed_plugins)
    else:
        to_remove = [p for p in installed_plugins if p.split("@")[0] in names]

    if not to_remove:
        click.echo("No plugins to remove.")
        return

    plugins_registry = _plugins_registry()

    for p in to_remove:
        plugin_id, _, version = p.partition("@")
        plugin_dir = plugins_registry / plugin_id / (version or "dev")

        if plugin_dir.exists():
            hooks_module = _load_hooks(plugin_dir)
            if hooks_module:
                project_ctx = ProjectContext(cwd)
                if hasattr(hooks_module, "before_remove"):
                    click.echo(f"🏃 Running before_remove hook for {plugin_id}...")
                    hooks_module.before_remove(project_ctx)
                if hasattr(hooks_module, "after_remove"):
                    click.echo(f"🏃 Running after_remove hook for {plugin_id}...")
                    hooks_module.after_remove(project_ctx)

        if p in installed_plugins:
            installed_plugins.remove(p)
            click.echo(f"✔ Removed {p} from project.")

        _unrecord_usage(plugins_registry, plugin_id, version, str(cwd))

    project_config["plugins"] = installed_plugins
    with open(project_yaml_file, "w") as f:
        yaml.dump(project_config, f)


@plugin_group.command(name="uninstall")
@click.argument("names", nargs=-1)
@click.option("--all", "uninstall_all", is_flag=True, help="Uninstall all plugins from the registry")
def uninstall_cmd(names, uninstall_all):
    """Delete plugin(s) from the global registry, if unused by any project."""
    plugins_registry = _plugins_registry()

    if uninstall_all:
        target_ids = [d.name for d in plugins_registry.iterdir() if d.is_dir()]
    else:
        target_ids = list(names)

    if not target_ids:
        click.echo("No plugins specified.")
        return

    for plugin_id in target_ids:
        plugin_root = plugins_registry / plugin_id
        if not plugin_root.exists():
            click.echo(f"⚠ Plugin '{plugin_id}' not found in registry.")
            continue

        usages = _all_usages(plugins_registry, plugin_id)
        if usages:
            click.echo(f"❌ Cannot uninstall '{plugin_id}'. Still used by:")
            for proj in usages:
                click.echo(f"   - {proj}")
            continue

        shutil.rmtree(plugin_root)
        click.echo(f"✔ Uninstalled '{plugin_id}' from registry.")


@plugin_group.command(name="list")
@click.option("--global", "show_global", is_flag=True, help="List plugins downloaded in the global registry")
def list_cmd(show_global):
    """List plugins (project-scoped by default, or --global for the registry)."""
    if show_global:
        plugins_registry = _plugins_registry()
        found = False
        click.echo("Global Registry Plugins:")
        for plugin_dir in sorted(plugins_registry.iterdir()):
            if not plugin_dir.is_dir():
                continue
            for version_dir in sorted(plugin_dir.iterdir()):
                if version_dir.is_dir() and (version_dir / "manifest.yaml").exists():
                    click.echo(f"✔ {plugin_dir.name}@{version_dir.name}")
                    found = True
        if not found:
            click.echo("No plugins installed in registry.")
        return

    cwd = Path.cwd()
    project_yaml_file = cwd / ".pyartisan" / "project.yaml"
    if not project_yaml_file.exists():
        click.echo("❌ Error: Not a pyartisan project.")
        return

    project_config = load_plugin_yaml(project_yaml_file)
    plugins = project_config.get("plugins", [])
    if not plugins:
        click.echo("No plugins installed.")
        return

    click.echo("Project Plugins:")
    for p in plugins:
        click.echo(f"✔ {p}")
