import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

import pytest

import pyartisan
from pyartisan.shared import updates


def test_version_matches_pyproject():
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)
    assert data["project"]["version"] == pyartisan.__version__


def test_parse_semver():
    assert updates.parse_semver("v1.10.0") == (1, 10, 0)
    assert updates.parse_semver("1.0.0") == (1, 0, 0)
    for bad in ("latest", "v2", "v1.0.0-rc1"):
        assert updates.parse_semver(bad) is None


def test_latest_version_numeric():
    assert updates.latest_version(["v1.9.0", "v1.10.0", "junk"]) == "1.10.0"
    assert updates.latest_version([]) is None


def _boom() -> list[str]:
    raise AssertionError("fetch must not be called")


def test_check_update_newer(tmp_path):
    cache = tmp_path / "c.json"
    assert updates.check_update("1.0.0", cache, 1000.0, lambda: ["v1.1.0"]) == "1.1.0"
    assert json.loads(cache.read_text(encoding="utf-8")) == {
        "checked_at": 1000.0,
        "latest": "1.1.0",
    }


def test_check_update_uses_fresh_cache(tmp_path):
    cache = tmp_path / "c.json"
    cache.write_text(json.dumps({"checked_at": 900.0, "latest": "1.2.0"}), encoding="utf-8")
    assert updates.check_update("1.0.0", cache, 1000.0, _boom) == "1.2.0"


def test_check_update_expired_cache_refetches(tmp_path):
    cache = tmp_path / "c.json"
    now = 100000.0
    cache.write_text(json.dumps({"checked_at": now - 90000, "latest": "1.2.0"}), encoding="utf-8")
    assert updates.check_update("1.0.0", cache, now, lambda: ["v1.3.0"]) == "1.3.0"


def test_check_update_corrupt_cache(tmp_path):
    cache = tmp_path / "c.json"
    cache.write_text("{not json", encoding="utf-8")
    assert updates.check_update("1.0.0", cache, 1000.0, lambda: ["v1.1.0"]) == "1.1.0"


def test_check_update_offline(tmp_path):
    cache = tmp_path / "c.json"
    assert updates.check_update("1.0.0", cache, 1000.0, lambda: []) is None
    assert not cache.exists()


def test_check_update_not_newer(tmp_path):
    cache = tmp_path / "c.json"
    assert updates.check_update("1.1.0", cache, 1000.0, lambda: ["v1.1.0"]) is None
    assert updates.check_update("2.0.0", tmp_path / "d.json", 1000.0, lambda: ["v1.1.0"]) is None


def test_install_hint():
    assert updates.install_hint("1.2.3") == (
        "uv tool install --force git+https://github.com/bijoaja/pyartisan@v1.2.3"
    )


def test_fetch_tags_parses_refs(monkeypatch):
    out = "abc\trefs/tags/v1.0.0\ndef\trefs/tags/v1.1.0\n"
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout=out)
    )
    assert updates.fetch_tags("https://x/y.git") == ["v1.0.0", "v1.1.0"]


@pytest.mark.parametrize(
    "result",
    [
        FileNotFoundError(),
        subprocess.TimeoutExpired("git", 5),
        SimpleNamespace(returncode=1, stdout=""),
    ],
)
def test_fetch_tags_failure(monkeypatch, result):
    def fake_run(*a, **k):
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert updates.fetch_tags("https://x/y.git") == []
