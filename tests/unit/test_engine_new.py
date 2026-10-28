from pathlib import Path

from pyartisan.core.engine import _template_meta


def test_template_meta_reads_id_and_version(tmp_path: Path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("id: custom-template\nversion: '2.5'\n", encoding="utf-8")
    name, version = _template_meta(manifest, "default-tpl", "1.0")
    assert name == "custom-template"
    assert version == "2.5"


def test_template_meta_warns_on_broken_yaml(tmp_path: Path, capsys):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(": [", encoding="utf-8")
    name, version = _template_meta(manifest, "default-tpl", "1.0")
    assert (name, version) == ("default-tpl", "1.0")
    captured = capsys.readouterr()
    assert "Using defaults" in captured.out


def test_template_meta_warns_on_non_mapping(tmp_path: Path, capsys):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("- a\n", encoding="utf-8")
    name, version = _template_meta(manifest, "default-tpl", "1.0")
    assert (name, version) == ("default-tpl", "1.0")
    captured = capsys.readouterr()
    assert "Using defaults" in captured.out


def test_template_meta_missing_file_returns_defaults(tmp_path: Path, capsys):
    missing = tmp_path / "does_not_exist.yaml"
    name, version = _template_meta(missing, "default-tpl", "1.0")
    assert (name, version) == ("default-tpl", "1.0")
    captured = capsys.readouterr()
    assert "Using defaults" not in captured.out


def test_new_does_not_change_cwd(monkeypatch, tmp_path):
    import os
    import subprocess

    import click

    from pyartisan.core.engine import dispatch_new

    monkeypatch.chdir(tmp_path)
    initial_cwd = os.getcwd()

    def fake_run(cmd, *a, **kw):
        if cmd[:2] == ["git", "clone"]:
            target = Path(cmd[-1])
            target.mkdir(parents=True, exist_ok=True)
            (target / ".pyartisan").mkdir(parents=True, exist_ok=True)
            (target / ".pyartisan" / "manifest.yaml").write_text(
                "id: tpl\nversion: '1.0'\n", encoding="utf-8"
            )
            (target / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    calls = []

    def record_run(cmd, *a, **kw):
        calls.append((cmd, kw.get("cwd")))
        return fake_run(cmd, *a, **kw)

    monkeypatch.setattr(subprocess, "run", record_run)
    monkeypatch.setattr(click, "confirm", lambda *a, **kw: True)

    dispatch_new("fastapi", "myproject")

    assert os.getcwd() == initial_cwd
    post_clone_calls = [c for c in calls if c[0][:2] != ["git", "clone"]]
    assert len(post_clone_calls) > 0
    for cmd, cwd in post_clone_calls:
        assert cwd == "myproject", f"Command {cmd} did not receive cwd='myproject'"
