import pytest
from pyartisan.core.exceptions import ManifestNotFound, ManifestError
from pyartisan.core.manifest import load_manifest


def test_manifest_load(tmp_path):
    with pytest.raises(ManifestNotFound):
        load_manifest(tmp_path)

    manifest_dir = tmp_path / ".pyartisan"
    manifest_dir.mkdir()
    (manifest_dir / "manifest.yaml").write_text("invalid: - [", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(tmp_path)

    (manifest_dir / "manifest.yaml").write_text("id: flaskiq\nframework: flask\n", encoding="utf-8")
    data = load_manifest(tmp_path)
    assert data["id"] == "flaskiq"
    assert data["framework"] == "flask"
