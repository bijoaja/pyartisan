import os
import re
from pathlib import Path

import yaml

from pyartisan.core.exceptions import ManifestError
from pyartisan.core.registration import apply_registration
from pyartisan.renderer import make_env
from pyartisan.utils.naming import name_parts


def requirement_name(spec: str) -> str:
    """Extract normalized requirement package name before version/marker specifiers."""
    raw = re.split(r"[<>=!~\[; ]", spec.strip())[0].lower()
    return raw.replace("_", "-").replace(".", "-")


def has_requirement(content: str, spec: str) -> bool:
    """Return True if content has a non-comment line matching spec's normalized name."""
    target_name = requirement_name(spec)
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        if requirement_name(stripped) == target_name:
            return True
    return False


def load_project_yaml(path: Path) -> dict:
    with open(path / "project.yaml") as f:
        return yaml.safe_load(f)


def load_template_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_plugin_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class ProjectContext:
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.project_yaml_path = project_path / ".pyartisan"
        self.project_config = load_project_yaml(self.project_yaml_path)
        self.framework = self.project_config["framework"]["name"]

        # Load template metadata dari global registry (~/.pyartisan/)
        template_name = self.project_config["template"]["name"]
        template_version = str(self.project_config["template"]["version"])
        self.global_registry = Path(os.path.expanduser("~")) / ".pyartisan"
        self.template_config_path = (
            self.global_registry / "templates" / template_name / template_version / "template.yaml"
        )
        if self.template_config_path.exists():
            self.template_config = load_template_yaml(self.template_config_path)
        else:
            self.template_config = {}

    def create_service(self, name: str, stub_path: str):
        # Resolve path dari template_config
        # e.g. paths.services: app/modules/{module}/service.py
        path_template = self.template_config.get("paths", {}).get("services")
        if not path_template:
            # Fallback path default
            path_template = (
                "app/services/{module}.py"
                if self.framework == "fastapi"
                else "app/service/{module}.py"
            )

        name_lower, name_title, name_snake, name_plural = name_parts(name)
        context = {
            "name": name,
            "name_lower": name_lower,
            "name_title": name_title,
            "name_snake": name_snake,
            "name_plural": name_plural,
        }

        stub_file = Path(stub_path)
        if not stub_file.exists():
            raise ManifestError(f"Stub not found: {stub_path}")

        # Resolve path tujuan menggunakan nama module/service
        dest_rel = path_template.replace("{module}", name_lower)
        dest_path = self.project_path / dest_rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(stub_file, encoding="utf-8") as f:
            template_data = f.read()
        rendered = make_env().from_string(template_data).render(context)
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(rendered)

    def register_router(self, name: str):
        # Dapatkan spesifikasi marker dari template.yaml
        # markers: routers: file: app/main.py, marker: "# pyartisan:routers"
        marker_cfg = self.template_config.get("markers", {}).get("routers", {})
        target_file_rel = marker_cfg.get("file")
        marker = marker_cfg.get("marker")

        if not target_file_rel or not marker:
            # Fallback
            target_file_rel = "app/main.py" if self.framework == "fastapi" else "app/main.py"
            marker = "# pyartisan:routers"

        target_file = self.project_path / target_file_rel
        name_lower, name_title, name_snake, name_plural = name_parts(name)
        context = {
            "name": name,
            "name_lower": name_lower,
            "name_title": name_title,
            "name_snake": name_snake,
            "name_plural": name_plural,
        }

        if self.framework == "fastapi":
            line_template = 'from app.modules.{{name_lower}}.router import router as {{name_lower}}_router\napp.include_router({{name_lower}}_router, prefix="/{{name_lower}}")'
        else:
            line_template = "from app.{{name_lower}}.routes import {{name_lower}}_bp\napp.register_blueprint({{name_lower}}_bp)"

        apply_registration(
            reg_type="marker",
            target_file=target_file,
            context=context,
            marker=marker,
            line_template=line_template,
        )

    def add_dependency(self, package_name: str):
        # Tambahkan package ke requirements.txt proyek jika ada
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text(encoding="utf-8")
            if not has_requirement(content, package_name):
                separator = "" if content.endswith("\n") or not content else "\n"
                req_file.write_text(content + separator + f"{package_name}\n", encoding="utf-8")
