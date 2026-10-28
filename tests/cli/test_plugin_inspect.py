import pytest
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
    assert result.exit_code == 1, result.output
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
    assert result.exit_code == 1, result.output
    assert "missing httpx" in result.output.lower()
    assert "plugin has issues" in result.output.lower()


def test_doctor_flags_missing_dep_with_similar_name(runner, in_tmp_cwd, plugin_project):
    root = in_tmp_cwd
    _pyartisan_dir, _home_dir = plugin_project
    plugin_src_dir = root / "httpx-plugin"
    plugin_src_dir.mkdir()
    manifest_content = {
        "id": "myhttpx",
        "name": "HTTPX Plugin",
        "version": "1.0.0",
        "dependencies": {"pip": ["httpx"]},
    }
    with open(plugin_src_dir / "manifest.yaml", "w", encoding="utf-8") as f:
        yaml.dump(manifest_content, f)

    runner.invoke(cli, ["plugin", "install", "myhttpx", "--local", str(plugin_src_dir)])
    runner.invoke(cli, ["plugin", "apply", "myhttpx"])

    # requirements.txt contains httpx-extra (which contains httpx as a substring)
    (root / "requirements.txt").write_text("httpx-extra\n", encoding="utf-8")
    result = runner.invoke(cli, ["plugin", "doctor"])
    assert result.exit_code == 1, result.output
    assert "missing httpx" in result.output.lower()


def test_cli_plugin_list_updates(runner, in_tmp_cwd, plugin_project):
    result = runner.invoke(cli, ["plugin", "list", "--updates"])
    assert result.exit_code == 0, result.output
    assert "no git-based plugins in registry" in result.output.lower()


def test_info_rejects_bad_name(runner, in_tmp_cwd, plugin_project):
    result = runner.invoke(cli, ["plugin", "info", "../evil"])
    assert result.exit_code != 0


def test_status_with_issues_exits_0(runner, in_tmp_cwd, plugin_project):
    pyartisan_dir, _home_dir = plugin_project
    project_cfg = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    project_cfg["plugins"] = ["missingplugin@1.0.0"]
    (pyartisan_dir / "project.yaml").write_text(yaml.dump(project_cfg), encoding="utf-8")

    result = runner.invoke(cli, ["plugin", "status"])
    assert result.exit_code == 0, result.output
    assert "issues found" in result.output.lower()


@pytest.mark.parametrize(
    "cmd",
    [
        ["plugin", "apply", "x"],
        ["plugin", "remove", "x"],
        ["plugin", "list"],
        ["plugin", "status"],
        ["plugin", "doctor"],
    ],
)
def test_not_a_project_exits_1(runner, in_tmp_cwd, fake_home, cmd):
    result = runner.invoke(cli, cmd)
    assert result.exit_code == 1, result.output
    assert "not a pyartisan project" in result.output.lower()


def test_update_pull_failure_exits_1(runner, in_tmp_cwd, plugin_project, monkeypatch):
    import subprocess

    _pyartisan_dir, home_dir = plugin_project
    p_dir = home_dir / ".pyartisan" / "plugins" / "pullfail" / "1.0.0"
    p_dir.mkdir(parents=True, exist_ok=True)
    (p_dir / ".git").mkdir()

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("git pull network err")),
    )
    result = runner.invoke(cli, ["plugin", "update", "pullfail"])
    assert result.exit_code == 1, result.output
    assert "failed to update" in result.output.lower()


def test_update_only_dev_links_exits_0(runner, in_tmp_cwd, plugin_project):
    _pyartisan_dir, home_dir = plugin_project
    p_dir = home_dir / ".pyartisan" / "plugins" / "devonly" / "dev"
    p_dir.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(cli, ["plugin", "update", "devonly"])
    assert result.exit_code == 0, result.output
    assert "no updatable plugin sources found" in result.output.lower()
