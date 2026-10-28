import os
from pathlib import Path

import yaml

from pyartisan.core.registration import apply_registration
from pyartisan.renderer import make_env
from pyartisan.utils.naming import name_parts


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

        # Resolve path tujuan menggunakan nama module/service
        dest_rel = path_template.replace("{module}", name_lower)
        dest_path = self.project_path / dest_rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Temukan file stub dari plugin lokal
        # (Selama runtime, plugins disalin ke ~/.pyartisan/plugins/)
        # stub_path relatif terhadap root plugin
        # project_context akan dipanggil oleh hooks.py yang tahu path plugin-nya
        full_stub_path = Path(stub_path)
        if not full_stub_path.is_absolute():
            # plugin_root akan dilewatkan atau disimpulkan
            pass

        # render stub ke service
        if Path(stub_path).exists():
            with open(stub_path) as f:
                template_data = f.read()
            rendered = make_env().from_string(template_data).render(context)
            with open(dest_path, "w") as f:
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
            content = req_file.read_text()
            if package_name not in content:
                req_file.write_text(content + f"\n{package_name}\n")
