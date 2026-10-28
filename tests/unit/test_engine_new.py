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
