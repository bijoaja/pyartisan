import subprocess
from types import SimpleNamespace

from pyartisan.shared import deps


def test_parse_uv_updates():
    output = "Update flask v3.0.0 -> v3.1.0\nResolved 40 packages"
    assert deps.parse_uv_updates(output) == [("flask", "3.0.0", "3.1.0")]


def test_parse_uv_updates_none():
    output = "Resolved 40 packages"
    assert deps.parse_uv_updates(output) == []


def test_parse_uv_updates_multiple():
    output = (
        "Resolved 42 packages in 12ms\n"
        "Update flask v3.0.0 -> v3.1.0\n"
        "Update requests v2.28.0 -> v2.31.0\n"
    )
    assert deps.parse_uv_updates(output) == [
        ("flask", "3.0.0", "3.1.0"),
        ("requests", "2.28.0", "2.31.0"),
    ]


def test_parse_pip_outdated():
    valid_json = '[{"name":"flask","version":"3.0.0","latest_version":"3.1.0"}]'
    assert deps.parse_pip_outdated(valid_json) == [("flask", "3.0.0", "3.1.0")]

    assert deps.parse_pip_outdated("not json") == []
    assert deps.parse_pip_outdated("{}") == []
    assert deps.parse_pip_outdated("[1, 2, 3]") == []
    assert deps.parse_pip_outdated("") == []


def test_find_outdated_none_without_files(tmp_path):
    assert deps.find_outdated(tmp_path) is None


def test_find_outdated_uv(tmp_path, monkeypatch):
    (tmp_path / "uv.lock").touch()
    monkeypatch.setattr(deps.shutil, "which", lambda cmd: "/usr/bin/uv" if cmd == "uv" else None)

    fake_output = "Update flask v3.0.0 -> v3.1.0\nResolved 40 packages"
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=fake_output, stderr=""),
    )

    result = deps.find_outdated(tmp_path)
    assert result == [("flask", "3.0.0", "3.1.0")]


def test_find_outdated_uv_error(tmp_path, monkeypatch):
    (tmp_path / "uv.lock").touch()
    monkeypatch.setattr(deps.shutil, "which", lambda cmd: "/usr/bin/uv")

    def _raise(*args, **kwargs):
        raise OSError("spawn failed")

    monkeypatch.setattr(subprocess, "run", _raise)
    assert deps.find_outdated(tmp_path) is None


def test_find_outdated_uv_non_zero(tmp_path, monkeypatch):
    (tmp_path / "uv.lock").touch()
    monkeypatch.setattr(deps.shutil, "which", lambda cmd: "/usr/bin/uv")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="error"),
    )
    assert deps.find_outdated(tmp_path) is None


def test_find_outdated_pip_needs_venv(tmp_path):
    (tmp_path / "requirements.txt").touch()
    assert deps.find_outdated(tmp_path) is None


def test_find_outdated_pip_with_venv(tmp_path, monkeypatch):
    (tmp_path / "requirements.txt").touch()
    fake_venv = tmp_path / "fake_venv"
    fake_python = fake_venv / "bin" / "python"

    monkeypatch.setattr(deps, "_find_project_venv", lambda cwd: fake_venv)
    monkeypatch.setattr(deps, "_venv_python", lambda venv: fake_python)

    fake_json = '[{"name":"requests","version":"2.25.0","latest_version":"2.31.0"}]'
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=fake_json, stderr=""),
    )

    result = deps.find_outdated(tmp_path)
    assert result == [("requests", "2.25.0", "2.31.0")]


def test_upgrade_uv_runs_lock_then_sync(tmp_path, monkeypatch):
    (tmp_path / "uv.lock").touch()
    monkeypatch.setattr(deps.shutil, "which", lambda cmd: "/usr/bin/uv" if cmd == "uv" else None)

    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    success = deps.upgrade(tmp_path)
    assert success is True
    assert calls == [["uv", "lock", "--upgrade"], ["uv", "sync"]]


def test_upgrade_uv_fails_if_lock_fails(tmp_path, monkeypatch):
    (tmp_path / "uv.lock").touch()
    monkeypatch.setattr(deps.shutil, "which", lambda cmd: "/usr/bin/uv")

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1),
    )

    assert deps.upgrade(tmp_path) is False


def test_upgrade_pip(tmp_path, monkeypatch):
    (tmp_path / "requirements.txt").touch()
    fake_venv = tmp_path / "fake_venv"
    fake_python = fake_venv / "bin" / "python"

    monkeypatch.setattr(deps, "_find_project_venv", lambda cwd: fake_venv)
    monkeypatch.setattr(deps, "_venv_python", lambda venv: fake_python)

    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    success = deps.upgrade(tmp_path)
    assert success is True
    assert calls == [[str(fake_python), "-m", "pip", "install", "-U", "-r", "requirements.txt"]]


def test_upgrade_pip_without_venv(tmp_path):
    (tmp_path / "requirements.txt").touch()
    assert deps.upgrade(tmp_path) is False


def test_upgrade_none_without_files(tmp_path):
    assert deps.upgrade(tmp_path) is False
