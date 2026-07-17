import os
import shutil
import subprocess
import urllib.request
import json
from pathlib import Path
import click
import yaml

from pyartisan.core.plugin_engine import ProjectContext, load_plugin_yaml, load_template_yaml


@click.group(name="plugin")
def plugin_group():
    """Manage PyArtisan plugins (community & marketplace)"""
    pass


def _verify_blockchain_license(plugin_id: str, license_key: str) -> bool:
    """Mock verification of blockchain license credential signature."""
    # Menghubungi node / API gateway blockchain mock
    # Untuk uji coba/demo, jika license_key valid (misal diawali 'valid-'), return True
    if license_key.startswith("valid-"):
        return True
    return False


@plugin_group.command(name="install")
@click.argument("name")
@click.option("--local", type=str, help="Install plugin from local directory path")
@click.option("--license", type=str, help="License key for premium marketplace plugins")
def install_cmd(name: str, local: str, license: str):
    """Install plugin into current project."""
    # Pastikan ini dijalankan di project PyArtisan
    cwd = Path.cwd()
    project_yaml_file = cwd / ".pyartisan" / "project.yaml"
    if not project_yaml_file.exists():
        click.echo("❌ Error: Not a pyartisan project. Missing .pyartisan/project.yaml.")
        return

    # Inisialisasi ProjectContext
    project_ctx = ProjectContext(cwd)

    # Direktori global registry
    global_registry = Path(os.path.expanduser("~")) / ".pyartisan"
    plugins_registry = global_registry / "plugins"
    plugins_registry.mkdir(parents=True, exist_ok=True)

    plugin_dir = None

    if local:
        local_path = Path(local)
        if not local_path.exists():
            click.echo(f"❌ Local path does not exist: {local}")
            return

        # Link lokal
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
    else:
        # Check jika premium/marketplace membutuhkan lisensi blockchain
        if license:
            click.echo("🔗 Verifying license credentials on Blockchain API node...")
            if not _verify_blockchain_license(name, license):
                click.echo("❌ Invalid license key or ownership validation failed on blockchain.")
                return
            click.echo("✔ License ownership successfully verified via Smart Contract.")
            # Mock secure download tarball premium plugin
            plugin_dir = plugins_registry / name / "1.0.0"
            plugin_dir.mkdir(parents=True, exist_ok=True)
            # Create dummy manifest untuk mock install
            manifest_data = {
                "id": name,
                "name": f"Premium {name}",
                "version": "1.0.0",
                "dependencies": {"pip": ["stripe"]}
            }
            with open(plugin_dir / "manifest.yaml", "w") as f:
                yaml.dump(manifest_data, f)
        else:
            # Komunitas (GitHub / Git URL)
            # Format name: github-user/repo-name
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

    # Verifikasi manifest.yaml plugin yang terinstal
    manifest_file = plugin_dir / "manifest.yaml"
    if not manifest_file.exists():
        click.echo("❌ Plugin is missing manifest.yaml.")
        return

    plugin_manifest = load_plugin_yaml(manifest_file)
    click.echo(f"📦 Installing plugin: {plugin_manifest.get('name', name)} ...")

    # Jalankan hooks.py jika ada
    hooks_file = plugin_dir / "hooks.py"
    if hooks_file.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("plugin_hooks", hooks_file)
        hooks_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hooks_module)

        # Lifecycle Hook: before_install
        if hasattr(hooks_module, "before_install"):
            click.echo("🏃 Running before_install hook...")
            hooks_module.before_install(project_ctx)

    # Tambahkan dependencies
    deps = plugin_manifest.get("dependencies", {})
    if deps and "pip" in deps:
        for pip_dep in deps["pip"]:
            click.echo(f"➕ Adding dependency: {pip_dep}")
            project_ctx.add_dependency(pip_dep)

    # Jalankan hooks.py: after_install
    if hooks_file.exists() and hasattr(hooks_module, "after_install"):
        click.echo("🏃 Running after_install hook...")
        hooks_module.after_install(project_ctx)

    # Catat plugin ke project.yaml lokal
    project_config = project_ctx.project_config
    if "plugins" not in project_config:
        project_config["plugins"] = []

    plugin_entry = f"{plugin_manifest['id']}@{plugin_manifest.get('version', 'dev')}"
    if plugin_entry not in project_config["plugins"]:
        project_config["plugins"].append(plugin_entry)
        with open(project_yaml_file, "w") as f:
            yaml.dump(project_config, f)

    click.echo(f"🎉 Plugin {plugin_manifest.get('name')} successfully installed!")
