import os
import shutil
import subprocess
import json
from pathlib import Path
import click
import yaml

from pyartisan.core.plugin_engine import ProjectContext, load_plugin_yaml
from pyartisan.renderer import render_stub
from pyartisan.utils.naming import name_parts

# Import all helpers from core and re-export for backward compatibility
from pyartisan.marketplace.core import (
    _global_registry,
    _plugins_registry,
    _usage_file,
    _load_usage,
    _save_usage,
    _record_usage,
    _unrecord_usage,
    _all_usages,
    _load_hooks,
    _verify_blockchain_license,
    _resolve_plugin_version,
    _find_registry_dir,
    _version_key,
    _latest_version,
    _check_updates,
)


@click.group(name="plugin")
def plugin_group():
    """Manage PyArtisan plugins (community & marketplace)"""
    pass


@plugin_group.command(name="init")
@click.argument("name")
def init_cmd(name: str):
    """Scaffold a new plugin skeleton, ready for development."""
    dest = Path.cwd() / name
    if dest.exists():
        click.echo(f"❌ Directory already exists: {dest}")
        return

    framework_choice = click.prompt(
        "Target framework?",
        type=click.Choice(["fastapi", "flask", "django", "all"]),
        default="all",
    )
    frameworks = (
        ["fastapi", "flask", "django"] if framework_choice == "all" else [framework_choice]
    )

    _, name_title, _, _ = name_parts(name)
    context = {"name": name, "name_title": name_title}

    template_dir = Path(__file__).parent.parent / "templates" / "plugin_init"
    render_stub(template_dir, dest, context)

    for fw in frameworks:
        fw_dir = dest / "stubs" / fw
        fw_dir.mkdir(parents=True, exist_ok=True)
        (fw_dir / ".gitkeep").touch()

    # Auto-register into the local registry (dev symlink) — same mechanism
    # `plugin install --local` uses. Registry key = `name` literal (e.g.
    # "crud-blogs"), matching manifest.yaml's `id` and what apply_cmd/
    # install_cmd look up.
    plugins_registry = _plugins_registry()
    plugin_dir = plugins_registry / name / "dev"
    plugin_dir.parent.mkdir(parents=True, exist_ok=True)
    if plugin_dir.exists() or plugin_dir.is_symlink():
        if plugin_dir.is_symlink():
            os.unlink(plugin_dir)
        else:
            shutil.rmtree(plugin_dir)
    os.symlink(dest.resolve(), plugin_dir, target_is_directory=True)

    click.echo(f"✔ Plugin skeleton created at {dest}")
    click.echo(f"✔ Linked to registry -> ~/.pyartisan/plugins/{name}/dev")
    click.echo(
        f"👉 Edit hooks.py and stubs/, then test with "
        f"`pyartisan plugin apply {name}` inside a sandbox project."
    )


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

    version = _resolve_plugin_version(plugin_root)
    if not version:
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
        plugin_dir = _find_registry_dir(plugins_registry, plugin_id, version)

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
@click.option("--updates", "show_updates", is_flag=True, help="Check for available updates on git-based registry plugins")
def list_cmd(show_global, show_updates):
    """List plugins (project-scoped by default, --global for the registry, --updates to check versions)."""
    if show_updates:
        _check_updates()
        return

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


@plugin_group.command(name="info")
@click.argument("name")
def info_cmd(name: str):
    """Show detailed metadata for a plugin in the global registry."""
    plugins_registry = _plugins_registry()
    plugin_root = plugins_registry / name
    if not plugin_root.exists():
        click.echo(f"❌ Plugin '{name}' not found in registry.")
        return

    version = _resolve_plugin_version(plugin_root)
    if not version:
        click.echo(f"❌ No installed version found for plugin '{name}'.")
        return

    manifest_file = plugin_root / version / "manifest.yaml"
    if not manifest_file.exists():
        click.echo("❌ Plugin is missing manifest.yaml.")
        return

    manifest = load_plugin_yaml(manifest_file)
    click.echo(f"Name         : {manifest.get('name', name)}")
    click.echo(f"ID           : {manifest.get('id', name)}")
    click.echo(f"Version      : {manifest.get('version', version)}")
    click.echo(f"Description  : {manifest.get('description', '-')}")
    click.echo(f"Author       : {manifest.get('author', '-')}")

    deps = manifest.get("dependencies", {}).get("pip", [])
    click.echo(f"Dependencies : {', '.join(deps) if deps else '-'}")

    env_vars = manifest.get("environment", [])
    click.echo(f"Environment  : {', '.join(env_vars) if env_vars else '-'}")

    usages = _all_usages(plugins_registry, name)
    click.echo(f"Used by      : {', '.join(usages) if usages else '(not applied to any project)'}")


@plugin_group.command(name="status")
def status_cmd():
    """Show plugin health status for the current project."""
    cwd = Path.cwd()
    project_yaml_file = cwd / ".pyartisan" / "project.yaml"
    if not project_yaml_file.exists():
        click.echo("❌ Error: Not a pyartisan project.")
        return

    project_config = load_plugin_yaml(project_yaml_file)
    click.echo(f"Project    : {project_config.get('project', {}).get('name', '-')}")
    click.echo(f"Framework  : {project_config.get('framework', {}).get('name', '-')}")

    plugins = project_config.get("plugins", [])
    if not plugins:
        click.echo("Plugins    : (none installed)")
        return

    plugins_registry = _plugins_registry()
    click.echo("Plugins:")
    all_ok = True
    for p in plugins:
        plugin_id, _, version = p.partition("@")
        plugin_dir = _find_registry_dir(plugins_registry, plugin_id, version)
        if plugin_dir.exists() and (plugin_dir / "manifest.yaml").exists():
            click.echo(f"✔ {p}")
        else:
            click.echo(f"✖ {p} (missing from registry)")
            all_ok = False

    click.echo(f"Health     : {'OK' if all_ok else 'ISSUES FOUND'}")


@plugin_group.command(name="doctor")
def doctor_cmd():
    """Diagnose plugin setup issues for the current project."""
    cwd = Path.cwd()
    project_yaml_file = cwd / ".pyartisan" / "project.yaml"
    if not project_yaml_file.exists():
        click.echo("❌ Error: Not a pyartisan project.")
        return

    project_config = load_plugin_yaml(project_yaml_file)
    all_ok = True

    if "framework" in project_config and "name" in project_config["framework"]:
        click.echo("✔ Manifest")
    else:
        click.echo("✖ Manifest (missing framework.name)")
        all_ok = False

    try:
        project_ctx = ProjectContext(cwd)
        click.echo("✔ Framework")
    except Exception as e:
        click.echo(f"✖ Framework ({e})")
        all_ok = False
        project_ctx = None

    if project_ctx is not None:
        if project_ctx.template_config:
            click.echo("✔ Template Metadata")
        else:
            click.echo("✖ Template Metadata (template.yaml not found in registry)")
            all_ok = False

    plugins_registry = _plugins_registry()
    plugins = project_config.get("plugins", [])
    for p in plugins:
        plugin_id, _, version = p.partition("@")
        plugin_dir = _find_registry_dir(plugins_registry, plugin_id, version)
        manifest_file = plugin_dir / "manifest.yaml"
        if not manifest_file.exists():
            click.echo(f"✖ Dependencies ({plugin_id}: manifest.yaml missing)")
            all_ok = False
            continue
        manifest = load_plugin_yaml(manifest_file)
        deps = manifest.get("dependencies", {}).get("pip", [])
        req_file = cwd / "requirements.txt"
        req_content = req_file.read_text() if req_file.exists() else ""
        missing = [d for d in deps if d not in req_content]
        if missing:
            click.echo(f"✖ Dependencies ({plugin_id}: missing {', '.join(missing)} in requirements.txt)")
            all_ok = False
        else:
            click.echo(f"✔ Dependencies ({plugin_id})")

    if project_ctx is not None:
        marker_cfg = project_ctx.template_config.get("markers", {}).get("routers", {})
        target_file_rel = marker_cfg.get("file")
        marker = marker_cfg.get("marker")
        if target_file_rel and marker:
            target_file = cwd / target_file_rel
            if target_file.exists() and marker in target_file.read_text():
                click.echo("✔ Marker")
            else:
                click.echo(f"✖ Marker ({marker} not found in {target_file_rel})")
                all_ok = False

    click.echo()
    click.echo("Plugin is valid" if all_ok else "Plugin has issues, see above.")
