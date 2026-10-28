import yaml

from pyartisan.cli import cli


def test_cli_plugin_info_status_doctor(runner, in_tmp_cwd, plugin_project):
    root = in_tmp_cwd
    pyartisan_dir, _home_dir = plugin_project

    plugin_src_dir = root / "my-plugin"
    plugin_src_dir.mkdir()
    manifest_content = {
        "id": "myplugin",
        "name": "My Local Plugin",
        "version": "1.0.0",
        "description": "Plugin uji coba",
        "author": "Tester",
        "dependencies": {"pip": ["httpx"]},
        "environment": ["MY_PLUGIN_KEY"],
    }
    with open(plugin_src_dir / "manifest.yaml", "w", encoding="utf-8") as f:
        yaml.dump(manifest_content, f)

    # plugin belum di-install: info gagal
    result = runner.invoke(cli, ["plugin", "info", "myplugin"])
    assert "not found in registry" in result.output.lower()

    # install + apply
    result = runner.invoke(cli, ["plugin", "install", "myplugin", "--local", str(plugin_src_dir)])
    assert result.exit_code == 0, result.output

    # info sebelum apply: "Used by" kosong
    result = runner.invoke(cli, ["plugin", "info", "myplugin"])
    assert result.exit_code == 0, result.output
    assert "my local plugin" in result.output.lower()
    assert "httpx" in result.output
    assert "my_plugin_key" in result.output.lower()
    assert "not applied to any project" in result.output.lower()

    result = runner.invoke(cli, ["plugin", "apply", "myplugin"])
    assert result.exit_code == 0, result.output

    # info setelah apply: "Used by" berisi path project
    result = runner.invoke(cli, ["plugin", "info", "myplugin"])
    assert str(root) in result.output

    # status: project sehat karena plugin ada di registry
    result = runner.invoke(cli, ["plugin", "status"])
    assert result.exit_code == 0, result.output
    assert "myplugin@1.0.0" in result.output
    assert "health     : ok" in result.output.lower()

    # doctor: semua check lolos
    result = runner.invoke(cli, ["plugin", "doctor"])
    assert result.exit_code == 0, result.output
    assert "plugin is valid" in result.output.lower()

    # doctor mendeteksi dependency belum ditambahkan ke requirements.txt
    (root / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    result = runner.invoke(cli, ["plugin", "doctor"])
    assert "missing httpx" in result.output.lower()
    assert "plugin has issues" in result.output.lower()


def test_cli_plugin_list_updates(runner, in_tmp_cwd, plugin_project):
    result = runner.invoke(cli, ["plugin", "list", "--updates"])
    assert result.exit_code == 0, result.output
    assert "no git-based plugins in registry" in result.output.lower()
