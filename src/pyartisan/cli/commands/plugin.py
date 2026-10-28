import os
import shutil
import subprocess
from pathlib import Path

import click
import yaml

from pyartisan.core.exceptions import PyArtisanError
from pyartisan.core.plugin_engine import (
    ProjectContext,
    has_requirement,
    load_plugin_yaml,
)
from pyartisan.marketplace.core import (
    _all_usages,
    _check_updates,
    _find_registry_dir,
    _load_hooks,
    _plugins_registry,
    _record_usage,
    _resolve_plugin_version,
    _unrecord_usage,
    _verify_blockchain_license,
)
from pyartisan.renderer import render_stub
from pyartisan.utils.naming import name_parts
from pyartisan.utils.safe import safe_child, validate_name


def _valid(value: str, what: str = "name") -> str:
    try:
        return validate_name(value, what)
    except PyArtisanError as e:
        raise click.ClickException(str(e)) from None


def _is_link(path: Path) -> bool:
    """True for a symlink, or a Windows junction (reparse point)."""
    if path.is_symlink():
        return True
    try:
        return bool(
            getattr(path.lstat(), "st_file_attributes", 0) & 0x400
        )  # FILE_ATTRIBUTE_REPARSE_POINT
    except OSError:
        return False


def _remove_link(path: Path) -> None:
    os.unlink(path) if path.is_symlink() else os.rmdir(
        path
    )  # rmdir drops a junction, not its target


def _confirm_hooks(plugin_id: str, version: str, plugin_dir: Path, assume_yes: bool) -> None:
    """Prompt for consent before executing untrusted plugin hooks.

    Dev links are trusted without a prompt. Non-interactive input or user
    rejection raises ClickException.
    """
    hooks_file = plugin_dir / "hooks.py"
    if not hooks_file.exists() or plugin_dir.name == "dev" or assume_yes:
        return

    prompt = (
        f"Plugin '{plugin_id}@{version}' includes hooks ({hooks_file}) "
        "that execute Python code with your privileges. Run hooks?"
    )
    try:
        approved = click.confirm(prompt, default=False)
    except click.Abort:
        approved = False

    if not approved:
        raise click.ClickException(
            "Plugin hooks were not approved. Re-run with --yes to allow them."
        )


def _link_dir(target: Path, link: Path) -> None:
    """Dev link to `target`. Windows without symlink privilege (WinError 1314): use a junction."""
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True
        )


@click.group(name="plugin")
def plugin_group():
    """Manage PyArtisan plugins (community & marketplace)"""
    pass


@plugin_group.command(name="init")
@click.argument("name")
def init_cmd(name: str):
    """Scaffold a new plugin skeleton, ready for development."""
    _valid(name, "plugin id")
    dest = Path.cwd() / name
    if dest.exists():
        raise click.ClickException(f"Directory already exists: {dest}")

    framework_choice = click.prompt(
        "Target framework?",
        type=click.Choice(["fastapi", "flask", "django", "all"]),
        default="all",
    )
    frameworks = ["fastapi", "flask", "django"] if framework_choice == "all" else [framework_choice]

    _, name_title, _, _ = name_parts(name)
    context = {"name": name, "name_title": name_title}

    template_dir = Path(__file__).parent.parent.parent / "templates" / "plugin_init"
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
    plugin_dir = safe_child(plugins_registry, name, "dev")
    plugin_dir.parent.mkdir(parents=True, exist_ok=True)
    if plugin_dir.exists() or _is_link(plugin_dir):
        if _is_link(plugin_dir):
            _remove_link(plugin_dir)
        else:
            shutil.rmtree(plugin_dir)
    _link_dir(dest.resolve(), plugin_dir)

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
        _valid(name, "plugin id")
        local_path = Path(local)
        if not local_path.exists():
            raise click.ClickException(f"Local path does not exist: {local}")

        plugin_dir = safe_child(plugins_registry, name, "dev")
        plugin_dir.parent.mkdir(parents=True, exist_ok=True)
        if plugin_dir.exists() or _is_link(plugin_dir):
            if _is_link(plugin_dir):
                _remove_link(plugin_dir)
            else:
                shutil.rmtree(plugin_dir)

        # Gunakan symlink (atau junction di Windows) untuk mode pengembangan
        _link_dir(local_path.resolve(), plugin_dir)
        click.echo(f"✔ Linked local plugin {name} -> {local_path}")
    elif license:
        _valid(name, "plugin id")
        click.echo("Note: license verification is an offline stub, no network check is performed.")
        click.echo("🔗 Verifying license credentials on Blockchain API node...")
        if not _verify_blockchain_license(name, license):
            raise click.ClickException(
                "Invalid license key or ownership validation failed on blockchain."
            )
        click.echo("✔ License ownership successfully verified via Smart Contract.")
        # Mock secure download tarball premium plugin
        plugin_dir = safe_child(plugins_registry, name, "1.0.0")
        plugin_dir.mkdir(parents=True, exist_ok=True)
        manifest_data = {
            "id": name,
            "name": f"Premium {name}",
            "version": "1.0.0",
            "dependencies": {"pip": ["stripe"]},
        }
        with open(plugin_dir / "manifest.yaml", "w", encoding="utf-8") as f:
            yaml.dump(manifest_data, f)
    else:
        # Komunitas (GitHub / Git URL). Format name: github-user/repo-name
        if "/" not in name:
            raise click.ClickException(
                "For community plugins, specify GitHub path 'github-username/repo-name'"
            )

        parts = name.split("/")
        if len(parts) != 2:
            raise click.ClickException(f"Invalid community plugin name: {name!r}")
        owner = _valid(parts[0], "owner")
        plugin_id = _valid(parts[1], "plugin id")

        repo_url = f"https://github.com/{owner}/{plugin_id}.git"
        plugin_dir = safe_child(plugins_registry, plugin_id, "1.0.0")

        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)

        click.echo(f"⬇ Cloning plugin from {repo_url}...")
        try:
            subprocess.run(
                ["git", "clone", "--", repo_url, str(plugin_dir)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            raise click.ClickException(f"Failed to clone plugin repository: {e}")

    manifest_file = plugin_dir / "manifest.yaml"
    if not manifest_file.exists():
        raise click.ClickException("Plugin is missing manifest.yaml.")

    plugin_manifest = load_plugin_yaml(manifest_file)
    if not isinstance(plugin_manifest, dict):
        raise click.ClickException("Plugin manifest.yaml is invalid or empty.")
    if "id" not in plugin_manifest or not plugin_manifest["id"]:
        raise click.ClickException("Plugin manifest is missing required 'id'.")
    manifest_id = _valid(str(plugin_manifest["id"]), "manifest id")

    click.echo(f"📦 Plugin '{plugin_manifest.get('name', name)}' downloaded to registry.")
    click.echo(f"👉 Run `pyartisan plugin apply {manifest_id}` inside a project to use it.")


@plugin_group.command(name="apply")
@click.argument("name")
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Automatically approve plugin hooks without prompting",
)
def apply_cmd(name: str, yes: bool):
    """Apply a registry-installed plugin to the current project."""
    _valid(name, "plugin id")
    cwd = Path.cwd()
    project_yaml_file = cwd / ".pyartisan" / "project.yaml"
    if not project_yaml_file.exists():
        raise click.ClickException("Not a pyartisan project. Missing .pyartisan/project.yaml.")

    plugins_registry = _plugins_registry()
    plugin_root = safe_child(plugins_registry, name)
    if not plugin_root.exists():
        raise click.ClickException(
            f"Plugin '{name}' not found in registry. Run `pyartisan plugin install {name}` first."
        )

    version = _resolve_plugin_version(plugin_root)
    if not version:
        raise click.ClickException(f"No installed version found for plugin '{name}'.")

    plugin_dir = safe_child(plugin_root, version)
    manifest_file = plugin_dir / "manifest.yaml"
    if not manifest_file.exists():
        raise click.ClickException("Plugin is missing manifest.yaml.")

    plugin_manifest = load_plugin_yaml(manifest_file)
    if not isinstance(plugin_manifest, dict):
        raise click.ClickException("Plugin manifest.yaml is invalid or empty.")
    if "id" not in plugin_manifest or not plugin_manifest["id"]:
        raise click.ClickException("Plugin manifest is missing required 'id'.")
    manifest_id = _valid(str(plugin_manifest["id"]), "manifest id")

    _confirm_hooks(manifest_id, version, plugin_dir, yes)

    project_ctx = ProjectContext(cwd)

    click.echo(f"📦 Applying plugin: {plugin_manifest.get('name', name)} ...")

    try:
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
    except Exception as e:
        raise click.ClickException(
            f"Plugin failed: {e}. Files already written were not rolled back."
        ) from None

    project_config = project_ctx.project_config
    if "plugins" not in project_config:
        project_config["plugins"] = []

    plugin_version = plugin_manifest.get("version", version)
    plugin_entry = f"{manifest_id}@{plugin_version}"
    if plugin_entry not in project_config["plugins"]:
        project_config["plugins"].append(plugin_entry)
        with open(project_yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(project_config, f)

    _record_usage(plugins_registry, manifest_id, plugin_version, str(cwd))

    click.echo(f"🎉 Plugin '{plugin_manifest.get('name')}' successfully applied to project!")


@plugin_group.command(name="update")
@click.argument("name")
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Automatically approve plugin hooks without prompting",
)
def update_cmd(name: str, yes: bool):
    """Update a registry plugin's git sources and re-apply if used by current project."""
    _valid(name, "plugin id")
    plugins_registry = _plugins_registry()
    plugin_root = safe_child(plugins_registry, name)
    if not plugin_root.exists():
        raise click.ClickException(f"Plugin '{name}' not found in registry.")

    version_dirs = [d for d in plugin_root.iterdir() if d.is_dir()]
    if not version_dirs:
        raise click.ClickException(f"No installed version found for plugin '{name}'.")

    updated_any = False
    has_errors = False
    for version_dir in version_dirs:
        if version_dir.name == "dev":
            click.echo("ℹ Skipping local dev link (already live from source path).")
            continue
        if (version_dir / ".git").exists():
            click.echo(f"⬆ Pulling latest changes for {name}@{version_dir.name}...")
            try:
                subprocess.run(
                    ["git", "-C", str(version_dir), "pull"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                updated_any = True
            except Exception as e:
                click.echo(f"❌ Failed to update {version_dir.name}: {e}")
                has_errors = True

    if not updated_any:
        click.echo("No updatable plugin sources found (only local dev links present).")
        if has_errors:
            raise click.exceptions.Exit(1)
        return

    if has_errors:
        raise click.exceptions.Exit(1)

    click.echo(f"✔ Plugin '{name}' updated in registry.")

    cwd = Path.cwd()
    project_yaml_file = cwd / ".pyartisan" / "project.yaml"
    if project_yaml_file.exists():
        project_config = load_plugin_yaml(project_yaml_file)
        if any(p.split("@")[0] == name for p in project_config.get("plugins", [])):
            click.echo("🔄 Re-applying updated plugin to current project...")
            ctx = click.get_current_context()
            ctx.invoke(apply_cmd, name=name, yes=yes)


@plugin_group.command(name="remove")
@click.argument("names", nargs=-1)
@click.option("--all", "remove_all", is_flag=True, help="Remove all plugins from project")
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Automatically approve plugin hooks without prompting",
)
def remove_cmd(names, remove_all, yes: bool):
    """Remove plugin(s) from the current project (registry copy stays intact)."""
    cwd = Path.cwd()
    project_yaml_file = cwd / ".pyartisan" / "project.yaml"
    if not project_yaml_file.exists():
        raise click.ClickException("Not a pyartisan project.")

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
    has_errors = False

    for p in to_remove:
        plugin_id, _, version = p.partition("@")
        try:
            plugin_dir = _find_registry_dir(plugins_registry, plugin_id, version)
        except PyArtisanError:
            click.echo(f"✖ {p} (invalid plugin entry)")
            has_errors = True
            continue

        if plugin_dir.exists():
            _confirm_hooks(plugin_id, version, plugin_dir, yes)
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
            project_config["plugins"] = list(installed_plugins)
            with open(project_yaml_file, "w", encoding="utf-8") as f:
                yaml.dump(project_config, f)
            click.echo(f"✔ Removed {p} from project.")

        _unrecord_usage(plugins_registry, plugin_id, version, str(cwd))

    project_config["plugins"] = installed_plugins
    with open(project_yaml_file, "w", encoding="utf-8") as f:
        yaml.dump(project_config, f)

    if has_errors:
        raise click.exceptions.Exit(1)


@plugin_group.command(name="uninstall")
@click.argument("names", nargs=-1)
@click.option(
    "--all", "uninstall_all", is_flag=True, help="Uninstall all plugins from the registry"
)
def uninstall_cmd(names, uninstall_all):
    """Delete plugin(s) from the global registry, if unused by any project."""
    plugins_registry = _plugins_registry()

    installed = {d.name for d in plugins_registry.iterdir() if d.is_dir()}
    if uninstall_all:
        target_ids = sorted(installed)
    else:
        target_ids = list(names)

    if not target_ids:
        click.echo("No plugins specified.")
        return

    has_errors = False
    for plugin_id in target_ids:
        if plugin_id in installed:
            plugin_root = safe_child(plugins_registry, plugin_id)
        else:
            _valid(plugin_id, "plugin id")
            plugin_root = safe_child(plugins_registry, plugin_id)
            if not plugin_root.exists():
                click.echo(f"⚠ Plugin '{plugin_id}' not found in registry.")
                has_errors = True
                continue

        usages = _all_usages(plugins_registry, plugin_id)
        if usages:
            click.echo(f"❌ Cannot uninstall '{plugin_id}'. Still used by:")
            for proj in usages:
                click.echo(f"   - {proj}")
            has_errors = True
            continue

        if _is_link(plugin_root):
            _remove_link(plugin_root)
        else:
            for child in plugin_root.iterdir():
                if _is_link(child):
                    _remove_link(child)
            shutil.rmtree(plugin_root)
        click.echo(f"✔ Uninstalled '{plugin_id}' from registry.")

    if has_errors:
        raise click.exceptions.Exit(1)


@plugin_group.command(name="list")
@click.option(
    "--global", "show_global", is_flag=True, help="List plugins downloaded in the global registry"
)
@click.option(
    "--updates",
    "show_updates",
    is_flag=True,
    help="Check for available updates on git-based registry plugins",
)
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
        raise click.ClickException("Not a pyartisan project.")

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
    _valid(name, "plugin id")
    plugins_registry = _plugins_registry()
    plugin_root = safe_child(plugins_registry, name)
    if not plugin_root.exists():
        raise click.ClickException(f"Plugin '{name}' not found in registry.")

    version = _resolve_plugin_version(plugin_root)
    if not version:
        raise click.ClickException(f"No installed version found for plugin '{name}'.")

    manifest_file = safe_child(plugin_root, version, "manifest.yaml")
    if not manifest_file.exists():
        raise click.ClickException("Plugin is missing manifest.yaml.")

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
        raise click.ClickException("Not a pyartisan project.")

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
        try:
            plugin_dir = _find_registry_dir(plugins_registry, plugin_id, version)
            if plugin_dir.exists() and (plugin_dir / "manifest.yaml").exists():
                click.echo(f"✔ {p}")
            else:
                click.echo(f"✖ {p} (missing from registry)")
                all_ok = False
        except PyArtisanError:
            click.echo(f"✖ {p} (invalid plugin entry)")
            all_ok = False

    click.echo(f"Health     : {'OK' if all_ok else 'ISSUES FOUND'}")


@plugin_group.command(name="doctor")
def doctor_cmd():
    """Diagnose plugin setup issues for the current project."""
    cwd = Path.cwd()
    project_yaml_file = cwd / ".pyartisan" / "project.yaml"
    if not project_yaml_file.exists():
        raise click.ClickException("Not a pyartisan project.")

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
        try:
            plugin_dir = _find_registry_dir(plugins_registry, plugin_id, version)
        except PyArtisanError:
            click.echo(f"✖ {p} (invalid plugin entry)")
            all_ok = False
            continue
        manifest_file = plugin_dir / "manifest.yaml"
        if not manifest_file.exists():
            click.echo(f"✖ Dependencies ({plugin_id}: manifest.yaml missing)")
            all_ok = False
            continue
        manifest = load_plugin_yaml(manifest_file)
        deps = manifest.get("dependencies", {}).get("pip", [])
        req_file = cwd / "requirements.txt"
        req_content = req_file.read_text(encoding="utf-8") if req_file.exists() else ""
        missing = [d for d in deps if not has_requirement(req_content, d)]
        if missing:
            click.echo(
                f"✖ Dependencies ({plugin_id}: missing {', '.join(missing)} in requirements.txt)"
            )
            all_ok = False
        else:
            click.echo(f"✔ Dependencies ({plugin_id})")

    if project_ctx is not None:
        marker_cfg = project_ctx.template_config.get("markers", {}).get("routers", {})
        target_file_rel = marker_cfg.get("file")
        marker = marker_cfg.get("marker")
        if target_file_rel and marker:
            target_file = cwd / target_file_rel
            if target_file.exists() and marker in target_file.read_text(encoding="utf-8"):
                click.echo("✔ Marker")
            else:
                click.echo(f"✖ Marker ({marker} not found in {target_file_rel})")
                all_ok = False

    click.echo()
    if not all_ok:
        click.echo("Plugin has issues, see above.")
        raise click.exceptions.Exit(1)
    click.echo("Plugin is valid")
