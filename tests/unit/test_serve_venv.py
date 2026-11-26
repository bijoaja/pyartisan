import shutil
import sys
from pathlib import Path

import pytest

import pyartisan.core.engine as engine


def test_serve_project_venv(monkeypatch, tmp_path):
    cwd = tmp_path
    assert engine._find_project_venv(cwd) is None  # no venv in project

    venv = cwd / ".venv"
    py = engine._venv_python(venv)
    py.parent.mkdir(parents=True)
    py.write_text("", encoding="utf-8")
    assert engine._find_project_venv(cwd) is None  # no pyvenv.cfg: not a venv
    (venv / "pyvenv.cfg").write_text("", encoding="utf-8")
    assert engine._find_project_venv(cwd) == venv

    # the env pyartisan itself runs in must never be picked up
    monkeypatch.setattr(sys, "prefix", str(venv))
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    assert engine._find_project_venv(cwd) is None
    monkeypatch.setenv("VIRTUAL_ENV", str(venv))  # VIRTUAL_ENV == own prefix: still skipped
    assert engine._find_project_venv(cwd) is None

    argv, env = engine._venv_command(venv, ["python3", "server.py"])
    assert argv == [str(py), "server.py"]  # python3 mapped to venv python
    assert env["VIRTUAL_ENV"] == str(venv)
    assert env["PATH"].startswith(str(engine._venv_bin(venv)))
    assert engine._venv_command(venv, ["no-such-tool", "x"])[0] == ["no-such-tool", "x"]


def _make_venv(path: Path) -> Path:
    py = engine._venv_python(path)
    py.parent.mkdir(parents=True)
    py.write_text("", encoding="utf-8")
    (path / "pyvenv.cfg").write_text("", encoding="utf-8")
    return path


def test_virtual_env_outside_project_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    other = _make_venv(tmp_path / "other-venv")
    monkeypatch.setenv("VIRTUAL_ENV", str(other))
    assert engine._find_project_venv(project) is None


def test_virtual_env_inside_project_accepted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    inside = _make_venv(project / "custom-env")
    monkeypatch.setenv("VIRTUAL_ENV", str(inside))
    assert engine._find_project_venv(project) == inside


def test_venv_command_resolves_only_in_venv_bin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    venv = _make_venv(tmp_path / "venv")
    seen: list[str | None] = []

    def fake_which(cmd: str, path: str | None = None, **kwargs: object) -> str | None:
        seen.append(path)
        return None

    monkeypatch.setattr(shutil, "which", fake_which)
    argv, _ = engine._venv_command(venv, ["ruff", "check"])
    assert argv == ["ruff", "check"]
    assert seen == [str(engine._venv_bin(venv))]
