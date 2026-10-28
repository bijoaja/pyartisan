import yaml
from pyartisan.cli import cli


def test_cli_plugin_lifecycle(runner, in_tmp_cwd, plugin_project):
    """Test alur lengkap: install (registry) -> apply (project) -> remove (project) -> uninstall (registry)."""
    root = in_tmp_cwd
    pyartisan_dir, _home_dir = plugin_project

    # Mock local plugin directory
    plugin_src_dir = root / "my-plugin"
    plugin_src_dir.mkdir()
    manifest_content = {
        "id": "myplugin",
        "name": "My Local Plugin",
        "version": "1.0.0",
        "dependencies": {"pip": ["httpx"]},
    }
    with open(plugin_src_dir / "manifest.yaml", "w", encoding="utf-8") as f:
        yaml.dump(manifest_content, f)

    # 1. install: download ke registry saja, project.yaml belum berubah
    result = runner.invoke(cli, ["plugin", "install", "myplugin", "--local", str(plugin_src_dir)])
    assert result.exit_code == 0, result.output
    assert "linked local plugin" in result.output.lower()
    assert "downloaded to registry" in result.output.lower()

    project_config = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "plugins" not in project_config or project_config["plugins"] == []

    # plugin list (project) masih kosong sebelum apply
    result = runner.invoke(cli, ["plugin", "list"])
    assert result.exit_code == 0, result.output
    assert "no plugins installed" in result.output.lower()

    # plugin list --global menunjukkan plugin yang sudah di-download
    result = runner.invoke(cli, ["plugin", "list", "--global"])
    assert result.exit_code == 0, result.output
    assert "myplugin@dev" in result.output

    # 2. apply: terapkan ke project
    result = runner.invoke(cli, ["plugin", "apply", "myplugin"])
    assert result.exit_code == 0, result.output
    assert "successfully applied" in result.output.lower()

    project_config = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "myplugin@1.0.0" in project_config["plugins"]
    assert "httpx" in (root / "requirements.txt").read_text(encoding="utf-8")

    # plugin list (project) sekarang menunjukkan plugin aktif
    result = runner.invoke(cli, ["plugin", "list"])
    assert "myplugin@1.0.0" in result.output

    # 3. uninstall langsung gagal karena masih dipakai project ini
    result = runner.invoke(cli, ["plugin", "uninstall", "myplugin"])
    assert result.exit_code == 0, result.output
    assert "still used by" in result.output.lower()

    # 4. remove dari project dulu
    result = runner.invoke(cli, ["plugin", "remove", "myplugin"])
    assert result.exit_code == 0, result.output
    assert "removed myplugin@1.0.0" in result.output.lower()

    project_config = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "myplugin@1.0.0" not in project_config["plugins"]

    # 5. baru sekarang uninstall dari registry berhasil
    result = runner.invoke(cli, ["plugin", "uninstall", "myplugin"])
    assert result.exit_code == 0, result.output
    assert "uninstalled 'myplugin'" in result.output.lower()

    result = runner.invoke(cli, ["plugin", "list", "--global"])
    assert "no plugins installed in registry" in result.output.lower()
