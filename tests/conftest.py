import os

import pytest
import yaml
from click.testing import CliRunner

import pyartisan.config as config


@pytest.fixture
def fake_home(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    orig_expanduser = os.path.expanduser

    def _fake_expanduser(path):
        if path == "~":
            return str(home)
        if path.startswith("~" + os.sep) or path.startswith("~/"):
            return str(home / path[2:])
        return orig_expanduser(path)

    monkeypatch.setattr(os.path, "expanduser", _fake_expanduser)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


@pytest.fixture
def in_tmp_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def plugin_project(tmp_path, fake_home):
    pyartisan_dir = tmp_path / ".pyartisan"
    pyartisan_dir.mkdir(parents=True, exist_ok=True)
    project_yaml_content = {
        "project": {"name": "sandbox"},
        "framework": {"name": "fastapi"},
        "template": {"name": "fastiq", "version": "1.0.0"},
    }
    with open(pyartisan_dir / "project.yaml", "w", encoding="utf-8") as f:
        yaml.dump(project_yaml_content, f)

    home_dir = fake_home
    global_pyartisan = home_dir / ".pyartisan"
    global_pyartisan.mkdir(parents=True, exist_ok=True)
    template_yaml_dir = global_pyartisan / "templates" / "fastiq" / "1.0.0"
    template_yaml_dir.mkdir(parents=True, exist_ok=True)
    template_yaml_content = {
        "markers": {
            "routers": {
                "file": "app/main.py",
                "marker": "# pyartisan:routers",
            }
        }
    }
    with open(template_yaml_dir / "template.yaml", "w", encoding="utf-8") as f:
        yaml.dump(template_yaml_content, f)

    main_py = tmp_path / "app" / "main.py"
    main_py.parent.mkdir(parents=True, exist_ok=True)
    main_py.write_text("# pyartisan:routers\n", encoding="utf-8")

    req_file = tmp_path / "requirements.txt"
    req_file.write_text("fastapi\n", encoding="utf-8")

    return pyartisan_dir, home_dir


@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    config_dir = tmp_path / ".pyartisan"
    config_path = config_dir / "config.toml"
    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)
    return config_dir, config_path
