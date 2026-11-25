import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from pyartisan.cli.commands.serve import serve_cmd
from pyartisan.core import engine
from pyartisan.core.exceptions import PyArtisanError


def test_auto_prefers_docker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd = tmp_path
    (cwd / "docker-compose.yml").write_text("services: {}", encoding="utf-8")
    monkeypatch.setattr(engine, "_docker_available", lambda: True)
    monkeypatch.setattr(engine, "_find_project_venv", lambda _cwd: cwd / "venv")
    monkeypatch.setattr(
        shutil, "which", lambda cmd, **kwargs: "/usr/bin/uv" if cmd == "uv" else None
    )

    manifest = {"scripts": {"serve": "uv run python server.py"}}
    mode = engine.select_serve_mode(cwd, manifest, forced=None)
    assert mode == "docker"


def test_auto_falls_to_venv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd = tmp_path
    monkeypatch.setattr(engine, "_docker_available", lambda: False)
    monkeypatch.setattr(engine, "_find_project_venv", lambda _cwd: cwd / "venv")
    monkeypatch.setattr(
        shutil, "which", lambda cmd, **kwargs: "/usr/bin/uv" if cmd == "uv" else None
    )

    manifest = {"scripts": {"serve": "python server.py"}}
    mode = engine.select_serve_mode(cwd, manifest, forced=None)
    assert mode == "venv"


def test_auto_falls_to_uv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd = tmp_path
    monkeypatch.setattr(engine, "_docker_available", lambda: False)
    monkeypatch.setattr(engine, "_find_project_venv", lambda _cwd: None)
    monkeypatch.setattr(
        shutil, "which", lambda cmd, **kwargs: "/usr/bin/uv" if cmd == "uv" else None
    )

    manifest = {"scripts": {"serve": "uv run python server.py"}}
    mode = engine.select_serve_mode(cwd, manifest, forced=None)
    assert mode == "uv"


def test_auto_none_available_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd = tmp_path
    monkeypatch.setattr(engine, "_docker_available", lambda: False)
    monkeypatch.setattr(engine, "_find_project_venv", lambda _cwd: None)
    monkeypatch.setattr(shutil, "which", lambda _cmd, **kwargs: None)

    manifest = {"scripts": {"serve": "python server.py"}}
    with pytest.raises(PyArtisanError, match="No docker-compose.yml active"):
        engine.select_serve_mode(cwd, manifest, forced=None)


def test_forced_docker_unavailable_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd = tmp_path
    monkeypatch.setattr(engine, "_docker_available", lambda: False)
    monkeypatch.setattr(engine, "_find_project_venv", lambda _cwd: cwd / "venv")
    manifest = {"scripts": {"serve": "python server.py"}}

    with pytest.raises(PyArtisanError, match="Docker mode requested"):
        engine.select_serve_mode(cwd, manifest, forced="docker")


def test_forced_uv_without_uv_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd = tmp_path
    monkeypatch.setattr(shutil, "which", lambda _cmd, **kwargs: None)
    manifest = {"scripts": {"serve_uv": "uv run python server.py"}}

    with pytest.raises(PyArtisanError, match="not found on PATH"):
        engine.select_serve_mode(cwd, manifest, forced="uv")


def test_forced_venv_without_venv_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd = tmp_path
    monkeypatch.setattr(engine, "_find_project_venv", lambda _cwd: None)
    manifest = {"scripts": {"serve": "python server.py"}}

    with pytest.raises(PyArtisanError, match="Venv mode requested"):
        engine.select_serve_mode(cwd, manifest, forced="venv")


def test_uv_mode_uses_serve_when_prefixed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd = tmp_path
    monkeypatch.setattr(
        shutil, "which", lambda cmd, **kwargs: "/usr/bin/uv" if cmd == "uv" else None
    )
    manifest = {"scripts": {"serve": "uv run python server.py"}}

    assert engine.select_serve_mode(cwd, manifest, forced="uv") == "uv"

    called_cmd = []

    def fake_run(cmd, **kwargs):
        called_cmd.extend(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(engine, "load_manifest", lambda _cwd: manifest)
    monkeypatch.setattr(Path, "cwd", lambda: cwd)

    engine.dispatch_serve(mode="uv")
    assert called_cmd == ["uv", "run", "python", "server.py"]


def test_uv_mode_uses_serve_uv_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd = tmp_path
    monkeypatch.setattr(
        shutil, "which", lambda cmd, **kwargs: "/usr/bin/uv" if cmd == "uv" else None
    )
    manifest = {
        "scripts": {
            "serve": "python server.py",
            "serve_uv": "uv run flask run --port 5000",
        }
    }

    assert engine.select_serve_mode(cwd, manifest, forced="uv") == "uv"

    called_cmd = []

    def fake_run(cmd, **kwargs):
        called_cmd.extend(cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(engine, "load_manifest", lambda _cwd: manifest)
    monkeypatch.setattr(Path, "cwd", lambda: cwd)

    engine.dispatch_serve(mode="uv")
    assert called_cmd == ["uv", "run", "flask", "run", "--port", "5000"]


def test_uv_mode_missing_command_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cwd = tmp_path
    monkeypatch.setattr(
        shutil, "which", lambda cmd, **kwargs: "/usr/bin/uv" if cmd == "uv" else None
    )
    manifest = {"scripts": {"serve": "python server.py"}}

    with pytest.raises(PyArtisanError, match="serve_uv"):
        engine.select_serve_mode(cwd, manifest, forced="uv")


def test_cli_rejects_two_mode_flags() -> None:
    runner = CliRunner()
    result = runner.invoke(serve_cmd, ["--docker", "--uv"])
    assert result.exit_code != 0
    assert "Cannot specify more than one serve mode" in result.output
