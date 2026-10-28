import pytest

from pyartisan.core.exceptions import PyArtisanError
from pyartisan.marketplace.core import (
    _find_registry_dir,
    _load_hooks,
    _resolve_plugin_version,
    _usage_file,
)


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


def test_load_hooks_raises_when_spec_missing(tmp_path, monkeypatch):
    import importlib.util
    from unittest.mock import MagicMock

    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "hooks.py").write_text("# dummy hooks", encoding="utf-8")

    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *a, **kw: None)
    with pytest.raises(ImportError, match="Cannot load hooks from"):
        _load_hooks(plugin_dir)

    fake_spec = MagicMock(loader=None)
    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *a, **kw: fake_spec)
    with pytest.raises(ImportError, match="Cannot load hooks from"):
        _load_hooks(plugin_dir)


def test_resolve_plugin_version_empty_dir_returns_none(tmp_path):
    empty_dir = tmp_path / "empty_plugin"
    empty_dir.mkdir()
    assert _resolve_plugin_version(empty_dir) is None
