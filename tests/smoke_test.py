"""Assert-based self-check for the PyArtisan refactor.

No pytest dependency required — run directly:
    PYTHONPATH=src python3 tests/smoke_test.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

from click.testing import CliRunner

from pyartisan.utils.naming import name_parts
from pyartisan.core.detector import detect_framework
from pyartisan.plugin_loader import load_plugin
from pyartisan.exceptions import PluginNotFound
import pyartisan.config as config
from pyartisan.cli import cli


def test_name_parts():
    assert name_parts("blog") == ("blog", "Blog")
    assert name_parts("blog_post") == ("blog_post", "BlogPost")
    assert name_parts("blog-post") == ("blog_post", "BlogPost")
    print("OK  name_parts")


def test_detect_framework():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        assert detect_framework(root) is None
        (root / "app.py").write_text("app = Flask(__name__)\n")
        assert detect_framework(root) == "flask"
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "main.py").write_text("app = FastAPI()\n")
        assert detect_framework(root) == "fastapi"
    print("OK  detect_framework")


def test_config_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        config.CONFIG_DIR = root / ".pyartisan"
        config.CONFIG_PATH = config.CONFIG_DIR / "config.toml"

        data = config.load()
        assert data == config.DEFAULT_CONFIG
        assert config.CONFIG_PATH.exists()

        config.save({**data, "theme": "dark", "default_framework": "fastapi"})
        reloaded = config.load()
        assert reloaded["theme"] == "dark"
        assert reloaded["default_framework"] == "fastapi"

        reset_data = config.reset()
        assert reset_data == config.DEFAULT_CONFIG
    print("OK  config load/save/reset")


def test_plugin_loader():
    plugin = load_plugin("flask")
    assert plugin.name == "flask"

    plugin = load_plugin("fastapi")
    assert plugin.name == "fastapi"

    try:
        load_plugin("django")
        raise AssertionError("expected PluginNotFound")
    except PluginNotFound:
        pass
    print("OK  plugin_loader")


def test_cli_end_to_end():
    runner = CliRunner()

    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0, result.output
    assert "pyartisan" in result.output

    result = runner.invoke(cli, ["doctor"])
    assert "Python" in result.output

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        config.CONFIG_DIR = root / ".pyartisan"
        config.CONFIG_PATH = config.CONFIG_DIR / "config.toml"
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0, result.output
        assert "default_framework" in result.output

    with runner.isolated_filesystem() as tmp_dir:
        Path("app.py").write_text("app = Flask(__name__)\n")
        result = runner.invoke(cli, ["make:model", "Post"])
        assert result.exit_code == 0, result.output
        assert Path("app/model/post.py").exists()

    with runner.isolated_filesystem() as tmp_dir:
        result = runner.invoke(cli, ["make:model", "Post"])
        assert result.exit_code != 0
        assert "cannot be detected" in result.output

    with runner.isolated_filesystem() as tmp_dir:
        result = runner.invoke(cli, ["make:model", "Post", "--framework", "flask"])
        assert result.exit_code == 0, result.output
        assert Path("app/model/post.py").exists()

    print("OK  cli end-to-end (version/doctor/config/make:model, detection + override)")


def main():
    test_name_parts()
    test_detect_framework()
    test_config_roundtrip()
    test_plugin_loader()
    test_cli_end_to_end()
    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
