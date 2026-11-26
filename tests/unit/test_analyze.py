import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from pyartisan.cli import cli
from pyartisan.cli.commands.analyze import analyze_cmd
from pyartisan.core import engine
from pyartisan.core.exceptions import ManifestError, ManifestNotFound, PyArtisanError


def test_steps_from_manifest() -> None:
    manifest: dict[str, Any] = {
        "scripts": {
            "analyze": [
                {"name": "lint", "cmd": "flake8 .", "fix": "autopep8 ."},
                {"name": "test-types", "cmd": "mypy src"},
            ]
        }
    }
    steps_check = engine.analyze_steps(manifest, fix=False)
    assert steps_check == [("lint", "flake8 ."), ("test-types", "mypy src")]

    steps_fix = engine.analyze_steps(manifest, fix=True)
    assert steps_fix == [("lint", "autopep8 ."), ("test-types", "mypy src")]


def test_steps_default_without_key(tmp_path: Path) -> None:
    manifest: dict[str, Any] = {}

    # Default without src or app
    steps = engine.analyze_steps(manifest, fix=False, cwd=tmp_path)
    assert steps == [
        ("ruff-check", "ruff check ."),
        ("ruff-format", "ruff format --check ."),
        ("bandit", "bandit -q -r . -c pyproject.toml"),
        ("mypy", "mypy ."),
    ]

    # With app dir
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    steps_app = engine.analyze_steps(manifest, fix=False, cwd=tmp_path)
    assert steps_app[2] == ("bandit", "bandit -q -r app -c pyproject.toml")
    app_dir.rmdir()

    # With src dir
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    steps_src = engine.analyze_steps(manifest, fix=False, cwd=tmp_path)
    assert steps_src[2] == ("bandit", "bandit -q -r src -c pyproject.toml")


def test_steps_fix_mode_swaps_cmd(tmp_path: Path) -> None:
    manifest: dict[str, Any] = {}
    steps = engine.analyze_steps(manifest, fix=True, cwd=tmp_path)
    assert steps == [
        ("ruff-check", "ruff check --fix ."),
        ("ruff-format", "ruff format ."),
        ("bandit", "bandit -q -r . -c pyproject.toml"),
        ("mypy", "mypy ."),
    ]


def _create_project_manifest(path: Path) -> None:
    manifest_dir = path / ".pyartisan"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "manifest.yaml").write_text(
        "id: demo\nframework: flask\n",
        encoding="utf-8",
    )


def test_analyze_all_pass_exit_0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _create_project_manifest(tmp_path)
    executed: list[list[str]] = []
    cwds: list[Any] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        executed.append(cmd)
        cwds.append(kwargs.get("cwd"))
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(engine, "_find_project_venv", lambda _cwd: None)

    runner = CliRunner()
    with runner.isolation():
        engine.dispatch_analyze(cwd=tmp_path)

    assert len(executed) == 4
    assert executed[0] == ["ruff", "check", "."]
    assert executed[1] == ["ruff", "format", "--check", "."]
    assert executed[2] == ["bandit", "-q", "-r", ".", "-c", "pyproject.toml"]
    assert executed[3] == ["mypy", "."]
    assert cwds == [tmp_path] * 4


def test_analyze_runs_all_even_if_one_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _create_project_manifest(tmp_path)
    executed: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        executed.append(cmd)
        # Fail the first check only
        rc = 1 if len(executed) == 1 else 0
        return subprocess.CompletedProcess(args=cmd, returncode=rc)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(engine, "_find_project_venv", lambda _cwd: None)

    with pytest.raises(SystemExit) as exc_info:
        engine.dispatch_analyze(cwd=tmp_path)

    assert exc_info.value.code == 1
    assert len(executed) == 4
    captured = capsys.readouterr().out
    assert "❌ ruff-check failed." in captured
    assert "✔ ruff-format passed." in captured
    assert "Some checks failed: ruff-check." in captured


def test_analyze_only_filters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _create_project_manifest(tmp_path)
    executed: list[list[str]] = []
    cwds: list[Any] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        executed.append(cmd)
        cwds.append(kwargs.get("cwd"))
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(engine, "_find_project_venv", lambda _cwd: None)

    engine.dispatch_analyze(only=("ruff-check", "mypy"), cwd=tmp_path)
    assert len(executed) == 2
    assert executed[0] == ["ruff", "check", "."]
    assert executed[1] == ["mypy", "."]
    assert cwds == [tmp_path] * 2


def test_analyze_unknown_only_lists_valid(tmp_path: Path) -> None:
    _create_project_manifest(tmp_path)
    with pytest.raises(PyArtisanError) as exc_info:
        engine.dispatch_analyze(only=("invalid-check",), cwd=tmp_path)

    msg = str(exc_info.value)
    assert "Unknown check 'invalid-check'." in msg
    assert "Available checks: ruff-check, ruff-format, bandit, mypy" in msg


def test_analyze_missing_tool_reports_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _create_project_manifest(tmp_path)
    executed: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        executed.append(cmd)
        if len(executed) == 1:
            raise FileNotFoundError("No such file or directory: 'ruff'")
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(engine, "_find_project_venv", lambda _cwd: None)

    with pytest.raises(SystemExit) as exc_info:
        engine.dispatch_analyze(cwd=tmp_path)

    assert exc_info.value.code == 1
    assert len(executed) == 4
    captured = capsys.readouterr().out
    assert "❌ ruff-check failed: tool 'ruff' not found." in captured
    assert "Some checks failed: ruff-check." in captured


def test_analyze_without_manifest_errors(tmp_path: Path) -> None:
    with pytest.raises(ManifestNotFound):
        engine.dispatch_analyze(cwd=tmp_path)

    runner = CliRunner()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(analyze_cmd)
    monkeypatch.undo()
    assert result.exit_code == 1
    assert "❌" in result.output


def test_cli_registers_analyze() -> None:
    assert "analyze" in cli.commands
    assert cli.commands["analyze"] is analyze_cmd


def test_steps_bandit_includes_src_and_app(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "app").mkdir()
    steps = engine.analyze_steps({}, cwd=tmp_path)
    assert steps[2] == ("bandit", "bandit -q -r src app -c pyproject.toml")


@pytest.mark.parametrize(
    "bad",
    [
        "ruff check .",
        [{"name": "ok", "cmd": "x"}, "oops"],
        ["oops"],
        [{"name": "a"}],
        [{"cmd": "x"}],
        [{"name": 1, "cmd": "x"}],
        [{"name": "a", "cmd": ["x"]}],
    ],
)
def test_malformed_analyze_raises(bad: Any) -> None:
    with pytest.raises(ManifestError, match="scripts.analyze"):
        engine.analyze_steps({"scripts": {"analyze": bad}})


def test_malformed_analyze_names_index() -> None:
    bad = [{"name": "ok", "cmd": "x"}, "oops"]
    with pytest.raises(ManifestError, match=r"\[1\]"):
        engine.analyze_steps({"scripts": {"analyze": bad}})


def test_empty_analyze_falls_back(tmp_path: Path) -> None:
    steps = engine.analyze_steps({"scripts": {"analyze": []}}, cwd=tmp_path)
    assert [s[0] for s in steps] == ["ruff-check", "ruff-format", "bandit", "mypy"]


def test_cli_malformed_analyze_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = tmp_path / ".pyartisan"
    d.mkdir()
    (d / "manifest.yaml").write_text(
        "id: demo\nframework: flask\nscripts:\n  analyze:\n    - nope\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(analyze_cmd)
    assert result.exit_code == 1
    assert "❌" in result.output
    assert "scripts.analyze[0]" in result.output
    assert "All checks passed" not in result.output


def test_analyze_zero_steps_refuses_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _create_project_manifest(tmp_path)
    monkeypatch.setattr(engine, "analyze_steps", lambda *a, **k: [])
    with pytest.raises(PyArtisanError, match="No checks to run"):
        engine.dispatch_analyze(cwd=tmp_path)


def test_analyze_tool_missing_from_venv_fails_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".pyartisan").mkdir()
    (tmp_path / ".pyartisan" / "manifest.yaml").write_text(
        "id: demo\nframework: flask\nscripts:\n  analyze:\n    - {name: lint, cmd: ruff check .}\n",
        encoding="utf-8",
    )
    venv = tmp_path / "venv"
    monkeypatch.setattr(engine, "_find_project_venv", lambda _cwd: venv)
    monkeypatch.setattr(shutil, "which", lambda _cmd, **kwargs: None)
    ran: list[Any] = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: ran.append(a))

    with pytest.raises(SystemExit) as exc_info:
        engine.dispatch_analyze(cwd=tmp_path)
    assert exc_info.value.code == 1
    assert ran == []
    assert "tool 'ruff' not found in project venv" in capsys.readouterr().out
