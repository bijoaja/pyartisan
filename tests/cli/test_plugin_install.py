import subprocess

import pytest

from pyartisan.cli import cli


def test_cli_plugin_install_blockchain_license(runner, in_tmp_cwd, plugin_project):
    result_premium = runner.invoke(
        cli, ["plugin", "install", "premium-plugin", "--license", "valid-12345"]
    )
    assert result_premium.exit_code == 0, result_premium.output
    assert "license ownership successfully verified" in result_premium.output.lower()

    result_invalid = runner.invoke(
        cli, ["plugin", "install", "premium-plugin", "--license", "invalid-key"]
    )
    assert "invalid license key" in result_invalid.output.lower()


def test_install_license_prints_stub_note(runner, in_tmp_cwd, plugin_project):
    result = runner.invoke(cli, ["plugin", "install", "premium-plugin", "--license", "valid-12345"])
    assert result.exit_code == 0, result.output
    assert "offline stub" in result.output.lower()
    assert "license ownership successfully verified" in result.output.lower()


def _src(root):
    src = root / "src"
    src.mkdir()
    (src / "manifest.yaml").write_text("id: p\nname: P\nversion: 1.0.0\n", encoding="utf-8")
    return src


@pytest.mark.parametrize(
    "args",
    [
        ["..", "--local", "SRC"],
        ["../x", "--local", "SRC"],
        ["..", "--license", "valid-1"],
        ["owner/.."],
        ["owner/."],
        ["../x/y"],
    ],
)
def test_install_rejects_bad_names(runner, in_tmp_cwd, plugin_project, monkeypatch, args):
    _pyartisan_dir, home = plugin_project
    src = _src(in_tmp_cwd)

    def _boom(*a, **k):
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(subprocess, "run", _boom)
    (home / ".pyartisan" / "plugins").mkdir(exist_ok=True)
    before = sorted(p.name for p in (home / ".pyartisan").iterdir())

    result = runner.invoke(
        cli, ["plugin", "install", *[str(src) if a == "SRC" else a for a in args]]
    )

    assert result.exit_code != 0, result.output
    assert sorted(p.name for p in (home / ".pyartisan").iterdir()) == before
    assert not (home / ".pyartisan" / "x").exists()
    assert list((home / ".pyartisan" / "plugins").iterdir()) == []


@pytest.mark.parametrize("pid", ["my.plugin", "42-crud"])
def test_install_accepts_dotted_and_numeric_ids(runner, in_tmp_cwd, plugin_project, pid):
    src = _src(in_tmp_cwd)
    result = runner.invoke(cli, ["plugin", "install", pid, "--local", str(src)])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    ("args", "expected_err"),
    [
        (["p", "--local", "nonexistent/path"], "local path does not exist"),
        (["p", "--license", "invalid-key"], "invalid license key"),
        (["invalidname"], "specify github path"),
    ],
)
def test_install_failures_exit_1(runner, in_tmp_cwd, plugin_project, args, expected_err):
    result = runner.invoke(cli, ["plugin", "install", *args])
    assert result.exit_code == 1, result.output
    assert expected_err in result.output.lower()


def test_install_missing_manifest_exits_1(runner, in_tmp_cwd, plugin_project):
    empty_src = in_tmp_cwd / "empty_src"
    empty_src.mkdir()
    result = runner.invoke(cli, ["plugin", "install", "nomanifest", "--local", str(empty_src)])
    assert result.exit_code == 1, result.output
    assert "missing manifest.yaml" in result.output.lower()
