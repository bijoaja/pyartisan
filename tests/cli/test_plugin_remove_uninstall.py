import pytest
import yaml

from pyartisan.cli import cli


def test_cli_plugin_remove_multi_and_all(runner, in_tmp_cwd, plugin_project):
    pyartisan_dir, _home_dir = plugin_project

    project_yaml_content = yaml.safe_load(
        (pyartisan_dir / "project.yaml").read_text(encoding="utf-8")
    )
    project_yaml_content["plugins"] = [
        "payment-midtrans@1.0.0",
        "auth-jwt@2.0.0",
        "docker-tools@1.2.1",
    ]
    with open(pyartisan_dir / "project.yaml", "w", encoding="utf-8") as f:
        yaml.dump(project_yaml_content, f)

    # Test list
    result = runner.invoke(cli, ["plugin", "list"])
    assert result.exit_code == 0, result.output
    assert "payment-midtrans@1.0.0" in result.output
    assert "auth-jwt@2.0.0" in result.output
    assert "docker-tools@1.2.1" in result.output

    # Test remove satu plugin dari project
    result = runner.invoke(cli, ["plugin", "remove", "payment-midtrans"])
    assert result.exit_code == 0, result.output
    assert "removed payment-midtrans@1.0.0" in result.output.lower()

    updated_config = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "payment-midtrans@1.0.0" not in updated_config["plugins"]
    assert "auth-jwt@2.0.0" in updated_config["plugins"]

    # Test remove banyak plugin sekaligus
    result = runner.invoke(cli, ["plugin", "remove", "auth-jwt", "docker-tools"])
    assert result.exit_code == 0, result.output
    updated_config2 = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert updated_config2["plugins"] == []

    # Re-populate untuk test --all
    project_yaml_content["plugins"] = ["payment-midtrans@1.0.0", "auth-jwt@2.0.0"]
    with open(pyartisan_dir / "project.yaml", "w", encoding="utf-8") as f:
        yaml.dump(project_yaml_content, f)

    result = runner.invoke(cli, ["plugin", "remove", "--all"])
    assert result.exit_code == 0, result.output
    updated_config3 = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert updated_config3["plugins"] == []


def _make_source(root, name="myplugin-src", plugin_id="myplugin"):
    src = root / name
    src.mkdir()
    (src / "manifest.yaml").write_text(
        yaml.dump({"id": plugin_id, "name": plugin_id, "version": "1.0.0"}), encoding="utf-8"
    )
    return src


@pytest.mark.parametrize("bad", ["..", "../x", "HOME_ABS", "myplugin/", "./myplugin", r"a\b"])
def test_uninstall_rejects_unsafe_names(runner, in_tmp_cwd, plugin_project, bad):
    _pyartisan_dir, home = plugin_project
    src = _make_source(in_tmp_cwd)
    result = runner.invoke(cli, ["plugin", "install", "myplugin", "--local", str(src)])
    assert result.exit_code == 0, result.output
    sentinel = home / ".pyartisan" / "config.toml"
    sentinel.write_text("x", encoding="utf-8")

    name = str(home) if bad == "HOME_ABS" else bad
    result = runner.invoke(cli, ["plugin", "uninstall", name])

    assert result.exit_code != 0, result.output
    assert sentinel.exists()
    assert (home / ".pyartisan" / "plugins" / "myplugin").exists()


def test_uninstall_keeps_dev_source(runner, in_tmp_cwd, plugin_project):
    _pyartisan_dir, home = plugin_project
    src = _make_source(in_tmp_cwd)
    result = runner.invoke(cli, ["plugin", "install", "myplugin", "--local", str(src)])
    assert result.exit_code == 0, result.output

    result = runner.invoke(cli, ["plugin", "uninstall", "myplugin"])

    assert result.exit_code == 0, result.output
    assert not (home / ".pyartisan" / "plugins" / "myplugin").exists()
    assert (src / "manifest.yaml").exists()


def test_uninstall_all_still_works(runner, in_tmp_cwd, plugin_project):
    _pyartisan_dir, home = plugin_project
    for pid in ("one", "two"):
        src = _make_source(in_tmp_cwd, name=f"{pid}-src", plugin_id=pid)
        result = runner.invoke(cli, ["plugin", "install", pid, "--local", str(src)])
        assert result.exit_code == 0, result.output

    result = runner.invoke(cli, ["plugin", "uninstall", "--all"])

    assert result.exit_code == 0, result.output
    registry = home / ".pyartisan" / "plugins"
    assert not (registry / "one").exists()
    assert not (registry / "two").exists()
    assert (home / ".pyartisan" / "templates").exists()


def test_uninstall_legacy_id_in_registry_still_removable(runner, in_tmp_cwd, plugin_project):
    _pyartisan_dir, home = plugin_project
    legacy = home / ".pyartisan" / "plugins" / "bad name"
    legacy.mkdir(parents=True)

    result = runner.invoke(cli, ["plugin", "uninstall", "bad name"])

    assert result.exit_code == 0, result.output
    assert not legacy.exists()


def test_uninstall_unknown_valid_name_warns(runner, in_tmp_cwd, plugin_project):
    result = runner.invoke(cli, ["plugin", "uninstall", "nope"])
    assert result.exit_code == 1, result.output
    assert "not found in registry" in result.output.lower()


def test_tampered_project_entries(runner, in_tmp_cwd, plugin_project):
    pyartisan_dir, home = plugin_project
    sentinel_dir = home / ".pyartisan" / "x"
    sentinel_dir.mkdir()
    (sentinel_dir / "keep.txt").write_text("k", encoding="utf-8")
    config = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    config["plugins"] = ["../x@1"]
    (pyartisan_dir / "project.yaml").write_text(yaml.dump(config), encoding="utf-8")

    result = runner.invoke(cli, ["plugin", "status"])
    assert result.exit_code == 0, result.output
    assert "✖" in result.output
    assert "invalid" in result.output.lower()

    result = runner.invoke(cli, ["plugin", "doctor"])
    assert result.exit_code == 1, result.output
    assert "✖ ../x@1" in result.output

    result = runner.invoke(cli, ["plugin", "remove", "--all"])
    assert result.exit_code == 1, result.output
    assert sorted(p.name for p in sentinel_dir.iterdir()) == ["keep.txt"]
    kept = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert kept["plugins"] == ["../x@1"]


def test_uninstall_multi_continues_and_exits_1(runner, in_tmp_cwd, plugin_project):
    _pyartisan_dir, home = plugin_project
    src = _make_source(in_tmp_cwd, name="myplugin-src", plugin_id="myplugin")
    res_inst = runner.invoke(cli, ["plugin", "install", "myplugin", "--local", str(src)])
    assert res_inst.exit_code == 0

    result = runner.invoke(cli, ["plugin", "uninstall", "nope", "myplugin"])
    assert result.exit_code == 1, result.output
    assert "not found in registry" in result.output.lower()
    assert "uninstalled 'myplugin'" in result.output.lower()
    assert not (home / ".pyartisan" / "plugins" / "myplugin").exists()


def test_remove_multi_continues_and_exits_1(runner, in_tmp_cwd, plugin_project):
    pyartisan_dir, home = plugin_project
    src = _make_source(in_tmp_cwd, name="good-src", plugin_id="good")
    runner.invoke(cli, ["plugin", "install", "good", "--local", str(src)])
    runner.invoke(cli, ["plugin", "apply", "good"])

    config = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    config["plugins"].append("../tampered@1.0.0")
    (pyartisan_dir / "project.yaml").write_text(yaml.dump(config), encoding="utf-8")

    result = runner.invoke(cli, ["plugin", "remove", "--all"])
    assert result.exit_code == 1, result.output
    assert "removed good@1.0.0" in result.output.lower()
    assert "invalid plugin entry" in result.output.lower()

    updated = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "good@1.0.0" not in updated["plugins"]
    assert "../tampered@1.0.0" in updated["plugins"]


def test_empty_states_exit_0(runner, in_tmp_cwd, plugin_project):
    # remove with nothing to remove
    res_rem = runner.invoke(cli, ["plugin", "remove", "nonexistent"])
    assert res_rem.exit_code == 0, res_rem.output
    assert "no plugins to remove" in res_rem.output.lower()

    # uninstall with no names
    res_uninst = runner.invoke(cli, ["plugin", "uninstall"])
    assert res_uninst.exit_code == 0, res_uninst.output
    assert "no plugins specified" in res_uninst.output.lower()

    # list with no plugins
    res_list = runner.invoke(cli, ["plugin", "list"])
    assert res_list.exit_code == 0, res_list.output
    assert "no plugins installed" in res_list.output.lower()
