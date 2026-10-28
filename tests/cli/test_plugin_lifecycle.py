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


def _setup_registry_plugin(
    home_dir, plugin_id="hooked", version="1.0.0", hooks_code=None, manifest_data=None
):
    plugin_dir = home_dir / ".pyartisan" / "plugins" / plugin_id / version
    plugin_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": plugin_id,
        "name": f"Test {plugin_id}",
        "version": version,
    }
    if manifest_data is not None:
        manifest.update(manifest_data)
    with open(plugin_dir / "manifest.yaml", "w", encoding="utf-8") as f:
        yaml.dump(manifest, f)
    if hooks_code is not None:
        with open(plugin_dir / "hooks.py", "w", encoding="utf-8") as f:
            f.write(hooks_code)
    return plugin_dir


def test_apply_without_yes_and_no_input_aborts(runner, in_tmp_cwd, plugin_project):
    marker_file = in_tmp_cwd / "marker.txt"
    hooks_code = (
        f"from pathlib import Path\n"
        f"Path({repr(str(marker_file))}).write_text('ran', encoding='utf-8')\n"
        f"def before_install(ctx):\n    pass\n"
    )
    pyartisan_dir, home_dir = plugin_project
    _setup_registry_plugin(home_dir, "hooked", "1.0.0", hooks_code=hooks_code)

    result = runner.invoke(cli, ["plugin", "apply", "hooked"])
    assert result.exit_code == 1, result.output
    assert not marker_file.exists()
    assert "plugin hooks were not approved" in result.output.lower()
    project_cfg = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "hooked@1.0.0" not in project_cfg.get("plugins", [])
    assert not (home_dir / ".pyartisan" / "plugins" / "hooked" / "usage.json").exists()


def test_apply_declined_prompt_aborts(runner, in_tmp_cwd, plugin_project):
    marker_file = in_tmp_cwd / "marker.txt"
    hooks_code = (
        f"from pathlib import Path\n"
        f"Path({repr(str(marker_file))}).write_text('ran', encoding='utf-8')\n"
        f"def before_install(ctx):\n    pass\n"
    )
    pyartisan_dir, home_dir = plugin_project
    _setup_registry_plugin(home_dir, "hooked", "1.0.0", hooks_code=hooks_code)

    result = runner.invoke(cli, ["plugin", "apply", "hooked"], input="n\n")
    assert result.exit_code == 1, result.output
    assert not marker_file.exists()
    assert "plugin hooks were not approved" in result.output.lower()
    project_cfg = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "hooked@1.0.0" not in project_cfg.get("plugins", [])
    assert not (home_dir / ".pyartisan" / "plugins" / "hooked" / "usage.json").exists()


def test_apply_accepts_prompt(runner, in_tmp_cwd, plugin_project):
    marker_file = in_tmp_cwd / "marker.txt"
    hooks_code = (
        f"from pathlib import Path\n"
        f"Path({repr(str(marker_file))}).write_text('ran', encoding='utf-8')\n"
        f"def before_install(ctx):\n    pass\n"
    )
    pyartisan_dir, home_dir = plugin_project
    _setup_registry_plugin(home_dir, "hooked", "1.0.0", hooks_code=hooks_code)

    result = runner.invoke(cli, ["plugin", "apply", "hooked"], input="y\n")
    assert result.exit_code == 0, result.output
    assert marker_file.exists()
    project_cfg = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "hooked@1.0.0" in project_cfg.get("plugins", [])


def test_apply_yes_flag_skips_prompt(runner, in_tmp_cwd, plugin_project):
    marker_file = in_tmp_cwd / "marker.txt"
    hooks_code = (
        f"from pathlib import Path\n"
        f"Path({repr(str(marker_file))}).write_text('ran', encoding='utf-8')\n"
        f"def before_install(ctx):\n    pass\n"
    )
    pyartisan_dir, home_dir = plugin_project
    _setup_registry_plugin(home_dir, "hooked", "1.0.0", hooks_code=hooks_code)

    result = runner.invoke(cli, ["plugin", "apply", "hooked", "--yes"])
    assert result.exit_code == 0, result.output
    assert marker_file.exists()
    project_cfg = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "hooked@1.0.0" in project_cfg.get("plugins", [])


def test_dev_link_runs_hooks_without_prompt(runner, in_tmp_cwd, plugin_project):
    marker_file = in_tmp_cwd / "marker_dev.txt"
    local_dir = in_tmp_cwd / "dev-plugin"
    local_dir.mkdir()
    with open(local_dir / "manifest.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"id": "devhook", "name": "Dev Hook", "version": "1.0.0"}, f)
    with open(local_dir / "hooks.py", "w", encoding="utf-8") as f:
        f.write(
            f"from pathlib import Path\n"
            f"Path({repr(str(marker_file))}).write_text('dev', encoding='utf-8')\n"
        )
    result_install = runner.invoke(cli, ["plugin", "install", "devhook", "--local", str(local_dir)])
    assert result_install.exit_code == 0, result_install.output

    result = runner.invoke(cli, ["plugin", "apply", "devhook"])
    assert result.exit_code == 0, result.output
    assert marker_file.exists()


def test_plugin_without_hooks_no_prompt(runner, in_tmp_cwd, plugin_project):
    _setup_registry_plugin(plugin_project[1], "nohooks", "1.0.0", hooks_code=None)
    result = runner.invoke(cli, ["plugin", "apply", "nohooks"])
    assert result.exit_code == 0, result.output


def test_remove_asks_per_plugin(runner, in_tmp_cwd, plugin_project):
    pyartisan_dir, home_dir = plugin_project
    _setup_registry_plugin(home_dir, "p1", "1.0.0", hooks_code="def before_remove(ctx): pass\n")
    _setup_registry_plugin(home_dir, "p2", "1.0.0", hooks_code="def before_remove(ctx): pass\n")

    res_app1 = runner.invoke(cli, ["plugin", "apply", "p1", "--yes"])
    assert res_app1.exit_code == 0, res_app1.output
    res_app2 = runner.invoke(cli, ["plugin", "apply", "p2", "--yes"])
    assert res_app2.exit_code == 0, res_app2.output

    project_cfg = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "p1@1.0.0" in project_cfg["plugins"]
    assert "p2@1.0.0" in project_cfg["plugins"]

    result = runner.invoke(cli, ["plugin", "remove", "--all"], input="y\nn\n")
    assert result.exit_code == 1, result.output
    assert "plugin hooks were not approved" in result.output.lower()

    project_cfg = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "p1@1.0.0" not in project_cfg["plugins"]
    assert "p2@1.0.0" in project_cfg["plugins"]


def test_update_reapply_asks_again(runner, in_tmp_cwd, plugin_project, monkeypatch):
    import subprocess

    pyartisan_dir, home_dir = plugin_project
    p_dir = _setup_registry_plugin(
        home_dir, "up1", "1.0.0", hooks_code="def before_install(ctx): pass\n"
    )
    (p_dir / ".git").mkdir()

    res_app = runner.invoke(cli, ["plugin", "apply", "up1", "--yes"])
    assert res_app.exit_code == 0, res_app.output

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0))

    res_no_yes = runner.invoke(cli, ["plugin", "update", "up1"])
    assert res_no_yes.exit_code == 1, res_no_yes.output
    assert "plugin hooks were not approved" in res_no_yes.output.lower()

    res_yes = runner.invoke(cli, ["plugin", "update", "up1", "--yes"])
    assert res_yes.exit_code == 0, res_yes.output
    assert "updated in registry" in res_yes.output.lower()


def test_failing_hook_leaves_project_unchanged(runner, in_tmp_cwd, plugin_project):
    pyartisan_dir, home_dir = plugin_project
    hooks_code = "def before_install(ctx):\n    raise RuntimeError('boom')\n"
    _setup_registry_plugin(home_dir, "failhook", "1.0.0", hooks_code=hooks_code)

    result = runner.invoke(cli, ["plugin", "apply", "failhook", "--yes"])
    assert result.exit_code == 1, result.output
    assert "boom" in result.output
    assert "not rolled back" in result.output.lower()

    project_cfg = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "failhook@1.0.0" not in project_cfg.get("plugins", [])
    assert not (home_dir / ".pyartisan" / "plugins" / "failhook" / "usage.json").exists()


def test_apply_bad_manifest_id(runner, in_tmp_cwd, plugin_project):
    _pyartisan_dir, home_dir = plugin_project
    _setup_registry_plugin(home_dir, "badid", "1.0.0", manifest_data={"id": "../escaped"})
    res1 = runner.invoke(cli, ["plugin", "apply", "badid", "--yes"])
    assert res1.exit_code == 1, res1.output
    assert "invalid manifest id" in res1.output.lower()

    _setup_registry_plugin(home_dir, "noid", "1.0.0", manifest_data={"id": ""})
    res2 = runner.invoke(cli, ["plugin", "apply", "noid", "--yes"])
    assert res2.exit_code == 1, res2.output
    assert "missing" in res2.output.lower()


def test_empty_manifest_is_clean_error(runner, in_tmp_cwd, plugin_project):
    _pyartisan_dir, home_dir = plugin_project
    local_dir = in_tmp_cwd / "empty-manifest-plugin"
    local_dir.mkdir()
    (local_dir / "manifest.yaml").write_text("", encoding="utf-8")
    res_install = runner.invoke(
        cli, ["plugin", "install", "emptyplugin", "--local", str(local_dir)]
    )
    assert res_install.exit_code == 1, res_install.output
    assert "invalid or empty" in res_install.output.lower()
    assert "Traceback" not in res_install.output

    p_dir = home_dir / ".pyartisan" / "plugins" / "emptyapply" / "1.0.0"
    p_dir.mkdir(parents=True, exist_ok=True)
    (p_dir / "manifest.yaml").write_text("", encoding="utf-8")
    res_apply = runner.invoke(cli, ["plugin", "apply", "emptyapply", "--yes"])
    assert res_apply.exit_code == 1, res_apply.output
    assert "invalid or empty" in res_apply.output.lower()
    assert "Traceback" not in res_apply.output
