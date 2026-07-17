import yaml
from pathlib import Path

def load_project_yaml(path: Path) -> dict:
    with open(path / "project.yaml", "r") as f:
        return yaml.safe_load(f)

def load_template_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def load_plugin_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)
