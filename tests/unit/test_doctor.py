import shutil
from pathlib import Path

from click.testing import CliRunner

import pyartisan.shared.doctor as doctor
from pyartisan import __version__
from pyartisan.cli.commands.doctor import doctor_cmd
from pyartisan.shared.updates import install_hint


def test_doctor_uv_and_pip(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda n: None)
    assert doctor._check_uv()[0] is True
    assert doctor._check_pip()[0] is False

    monkeypatch.setattr(shutil, "which", lambda n: "/x/uv" if n == "uv" else None)
    assert doctor._check_pip()[0] is True


def test_doctor_reports_new_version(monkeypatch):
    monkeypatch.setattr(doctor, "check_update", lambda *args, **kwargs: "1.1.0")
    monkeypatch.setattr(doctor, "find_outdated", lambda *args, **kwargs: None)
    runner = CliRunner()
    result = runner.invoke(doctor_cmd)
    assert result.exit_code == 0
    assert f"pyartisan {__version__} -> 1.1.0 available" in result.output
    assert install_hint("1.1.0") in result.output


def test_doctor_skips_deps_outside_project(monkeypatch, tmp_path: Path):
    called = False

    def fake_find_outdated(cwd: Path):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(doctor, "check_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(doctor, "find_outdated", fake_find_outdated)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(doctor_cmd)
    assert result.exit_code == 0
    assert called is False


def test_doctor_lists_outdated_in_project(monkeypatch, tmp_path: Path):
    manifest_dir = tmp_path / ".pyartisan"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text("id: demo\nframework: flask\n", encoding="utf-8")

    monkeypatch.setattr(doctor, "check_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(doctor, "find_outdated", lambda cwd: [("flask", "3.0.0", "3.1.0")])
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(doctor_cmd)
    assert result.exit_code == 0
    assert "flask 3.0.0 -> 3.1.0" in result.output


def test_doctor_outdated_does_not_fail(monkeypatch, tmp_path: Path):
    manifest_dir = tmp_path / ".pyartisan"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text("id: demo\nframework: flask\n", encoding="utf-8")

    monkeypatch.setattr(doctor, "check_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(doctor, "find_outdated", lambda cwd: [("flask", "3.0.0", "3.1.0")])
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(doctor_cmd)
    assert result.exit_code == 0
    assert "flask 3.0.0 -> 3.1.0" in result.output


def test_doctor_warns_when_deps_skipped_in_project(monkeypatch, tmp_path: Path):
    manifest_dir = tmp_path / ".pyartisan"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text("id: demo\nframework: flask\n", encoding="utf-8")

    monkeypatch.setattr(doctor, "check_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(doctor, "find_outdated", lambda cwd: None)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(doctor_cmd)
    assert result.exit_code == 0
    assert (
        "Project dependencies check skipped (no lockfile/requirements or tools unavailable)."
        in result.output
    )


def test_doctor_upgrade_confirms(monkeypatch, tmp_path: Path):
    manifest_dir = tmp_path / ".pyartisan"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text("id: demo\nframework: flask\n", encoding="utf-8")

    monkeypatch.setattr(doctor, "check_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(doctor, "find_outdated", lambda cwd: [("flask", "3.0.0", "3.1.0")])

    upgraded = []
    monkeypatch.setattr(doctor, "upgrade_deps", lambda cwd: (upgraded.append(True), True)[1])
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()

    # Decline upgrade
    res_n = runner.invoke(doctor_cmd, ["--upgrade"], input="n\n")
    assert res_n.exit_code == 0
    assert len(upgraded) == 0

    # Accept upgrade
    res_y = runner.invoke(doctor_cmd, ["--upgrade"], input="y\n")
    assert res_y.exit_code == 0
    assert len(upgraded) == 1
    assert "Dependencies upgraded successfully." in res_y.output


def test_doctor_upgrade_failure_reported(monkeypatch, tmp_path: Path):
    manifest_dir = tmp_path / ".pyartisan"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text("id: demo\nframework: flask\n", encoding="utf-8")

    monkeypatch.setattr(doctor, "check_update", lambda *args, **kwargs: None)
    monkeypatch.setattr(doctor, "find_outdated", lambda cwd: [("flask", "3.0.0", "3.1.0")])
    monkeypatch.setattr(doctor, "upgrade", lambda cwd: False)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    res = runner.invoke(doctor_cmd, ["--upgrade"], input="y\n")
    assert res.exit_code == 0
    assert "Upgrade failed." in res.output
