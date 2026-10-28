import os
from pathlib import Path

from pyartisan.utils import console


def apply_registration(
    reg_type: str, target_file: Path, context: dict, marker: str = None, line_template: str = None
) -> None:
    """Apply import list or marker-based registration into target_file."""
    os.makedirs(target_file.parent, exist_ok=True)

    # Variable context unpack
    name_lower = context.get("name_lower", "")
    name_title = context.get("name_title", "")

    if reg_type == "import_list":
        # Strategy 1: import_list (mirror pyartisan.utils.fs.write_service_init)
        file_stem = f"{name_lower}_controller" if "controller" in str(target_file) else name_lower
        # Jika service, bedakan view/api
        if "service" in str(target_file):
            file_stem = f"{name_lower}_service"
            class_name = (
                f"{name_title}ApiService" if "api" in str(target_file) else f"{name_title}Service"
            )
        elif "repository" in str(target_file):
            file_stem = f"{name_lower}_repository"
            class_name = f"{name_title}Repository"
        elif "model" in str(target_file):
            class_name = name_title
        else:
            class_name = name_title

        import_line = f"from .{file_stem} import {class_name}"
        all_entry = f'"{class_name}"'

        if not target_file.exists():
            target_file.write_text(f"{import_line}\n\n__all__ = [{all_entry}]\n")
            console.success(f"created: {target_file}")
            return

        content = target_file.read_text()
        if import_line in content:
            return  # already registered

        lines = content.splitlines()
        new_lines = []
        all_updated = False
        insert_at = 0

        for i, line in enumerate(lines):
            if line.strip().startswith("__all__") and not all_updated:
                insert_at = i
                stripped = line.rstrip()
                if stripped.endswith("]"):
                    line = stripped[:-1].rstrip() + f", {all_entry}]"
                all_updated = True
            new_lines.append(line)

        new_lines.insert(insert_at, import_line)
        if not all_updated:
            new_lines.append(f"\n__all__ = [{all_entry}]")

        target_file.write_text("\n".join(new_lines) + "\n")
        console.success(f"updated: {target_file}")

    elif reg_type == "marker":
        # Strategy 2: marker comment insertion
        if not marker or not line_template:
            return

        # Render target line (e.g. app.include_router({{name_lower}}_router) -> app.include_router(users_router))
        from jinja2 import Environment

        target_line = Environment().from_string(line_template).render(context)

        if not target_file.exists():
            # Create file with marker
            target_file.write_text(f"{marker}\n{target_line}\n")
            console.success(f"created: {target_file}")
            return

        content = target_file.read_text()
        if target_line in content:
            return  # already registered

        if marker not in content:
            # Fallback append if marker is missing
            target_file.write_text(content + f"\n{target_line}\n")
            console.success(f"updated: {target_file}")
            return

        lines = content.splitlines()
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if marker in line:
                new_lines.append(target_line)

        target_file.write_text("\n".join(new_lines) + "\n")
        console.success(f"updated: {target_file}")
