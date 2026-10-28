import subprocess
from pathlib import Path

import pytest

import pyartisan.config as config
from pyartisan.cli import cli
from pyartisan.cli.commands.config import config_group


def test_config_roundtrip(isolated_config):
    data = config.load()
    assert data["theme"] == "default"
    assert "templates" in data
    assert data["templates"]["flask"] == "https://github.com/bijoaja/flaskiq.git"

    config.save({**data, "theme": "dark"})
    reloaded = config.load()
    assert reloaded["theme"] == "dark"


@pytest.mark.parametrize(
    "bad_url",
    ["-oProxyCommand=x", "http://h/r", "/local/dir"],
)
def test_config_set_rejects_bad_template_url(runner, isolated_config, bad_url):
    orig = config.load()
    orig_flask = orig["templates"]["flask"]

    result = runner.invoke(config_group, ["set", "--", "templates.flask", bad_url])

    assert result.exit_code != 0
    reloaded = config.load()
    assert reloaded["templates"]["flask"] == orig_flask


@pytest.mark.parametrize(
    "good_url",
    [
        "https://github.com/bijoaja/flaskiq.git",
        "ssh://git@host/o/r.git",
        "git@github.com:o/r.git",
    ],
)
def test_config_set_accepts_good_urls(runner, isolated_config, good_url):
    result = runner.invoke(config_group, ["set", "templates.flask", good_url])
    assert result.exit_code == 0, result.output
    reloaded = config.load()
    assert reloaded["templates"]["flask"] == good_url


def test_config_set_rejects_bad_sub_key(runner, isolated_config):
    orig = config.load()
    result = runner.invoke(
        config_group, ["set", "templates.../x", "https://github.com/bijoaja/flaskiq.git"]
    )
    assert result.exit_code != 0
    reloaded = config.load()
    assert reloaded == orig


def test_dispatch_new_rejects_tampered_config(runner, isolated_config, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    data = config.load()
    data["templates"] = {**data["templates"], "flask": "--upload-pack=x"}
    config.save(data)

    def _boom(*a, **k):
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(subprocess, "run", _boom)

    result = runner.invoke(cli, ["new", "flask", "app"])
    assert result.exit_code == 1
    assert "invalid template url" in result.output.lower()


def test_clone_uses_double_dash(runner, isolated_config, fake_home, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    calls = []

    class DummyCompletedProcess:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, *args, **kwargs):
        calls.append(list(cmd))
        if cmd[0:2] == ["git", "clone"]:
            target_dir = Path(cmd[-1])
            manifest_dir = target_dir / ".pyartisan"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            (manifest_dir / "manifest.yaml").write_text(
                "id: flaskiq\nversion: 1.0\n", encoding="utf-8"
            )
        return DummyCompletedProcess()

    monkeypatch.setattr(subprocess, "run", _fake_run)

    # 1. new flask app
    result = runner.invoke(cli, ["new", "flask", "app"], input="n\n")
    assert result.exit_code == 0, result.output
    first_cmd = calls[0]
    expected_url = config.load()["templates"]["flask"]
    assert "--" in first_cmd, f"Expected '--' in clone argv: {first_cmd}"
    dash_idx = first_cmd.index("--")
    assert first_cmd[dash_idx : dash_idx + 3] == ["--", expected_url, "app"]

    # 2. plugin install community clone
    plugin_calls = []

    def _fake_plugin_run(cmd, *args, **kwargs):
        plugin_calls.append(list(cmd))
        if cmd[0:2] == ["git", "clone"]:
            target_dir = Path(cmd[-1])
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "manifest.yaml").write_text(
                "id: testplug\nname: Test Plug\nversion: 1.0.0\n", encoding="utf-8"
            )
        return DummyCompletedProcess()

    monkeypatch.setattr(subprocess, "run", _fake_plugin_run)
    res_plugin = runner.invoke(cli, ["plugin", "install", "someuser/testplug"])
    assert res_plugin.exit_code == 0, res_plugin.output
    clone_cmds = [c for c in plugin_calls if c[0:2] == ["git", "clone"]]
    assert len(clone_cmds) == 1
    p_cmd = clone_cmds[0]
    assert "--" in p_cmd, f"Expected '--' in plugin clone argv: {p_cmd}"
    p_dash_idx = p_cmd.index("--")
    assert p_cmd[p_dash_idx : p_dash_idx + 2] == ["--", "https://github.com/someuser/testplug.git"]
