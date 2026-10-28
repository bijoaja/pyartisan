import pytest

from pyartisan.core.exceptions import PyArtisanError
from pyartisan.marketplace.core import _find_registry_dir, _usage_file


def test_usage_file_rejects_traversal(tmp_path):
    with pytest.raises(PyArtisanError):
        _usage_file(tmp_path / "reg", "../x")


@pytest.mark.parametrize(("pid", "version"), [("..", "1"), ("ok", "../..")])
def test_find_registry_dir_rejects_traversal(tmp_path, pid, version):
    with pytest.raises(PyArtisanError):
        _find_registry_dir(tmp_path / "reg", pid, version)


def test_find_registry_dir_normal(tmp_path):
    reg = tmp_path / "reg"
    (reg / "ok" / "1.0.0").mkdir(parents=True)
    assert _find_registry_dir(reg, "ok", "1.0.0") == reg / "ok" / "1.0.0"
