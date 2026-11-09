import os
from pathlib import Path

from pyartisan.renderer import make_env
from pyartisan.utils import console


def apply_registration(
    reg_type: str,
    target_file: Path,
    context: dict,
    marker: str | None = None,
    line_template: str | None = None,
) -> None:
    """Apply import list or marker-based registration into target_file."""
    os.makedirs(target_file.parent, exist_ok=True)

    # Variable context unpack
    name_lower = context.get("name_lower", "")
    name_title = context.get("name_title", "")

    if reg_type == "import_list":
        # Strategy 1: import_list (mirror pyartisan.utils.fs.write_service_init)
        file_stem = name_lower
        path_parts = {p.lower() for p in target_file.parts}
        if "controller" in path_parts or "controllers" in path_parts:
            file_stem = f"{name_lower}_controller"
            class_name = (
                f"{name_title}ApiController" if "api" in path_parts else f"{name_title}Controller"
            )
        # Jika service, bedakan view/api
        elif "service" in path_parts or "services" in path_parts:
            file_stem = f"{name_lower}_service"
            class_name = (
                f"{name_title}ApiService" if "api" in path_parts else f"{name_title}Service"
            )
        elif "repository" in path_parts or "repositories" in path_parts:
            file_stem = f"{name_lower}_repository"
            class_name = f"{name_title}Repository"
        elif "model" in path_parts or "models" in path_parts:
            class_name = name_title
        elif "routes" in path_parts or "route" in path_parts:
            file_stem = f"view.{name_lower}" if target_file.parent.name != "view" else name_lower
            class_name = f"{name_lower}_bp"
        else:
            class_name = name_title

        import_line = f"from .{file_stem} import {class_name}"
        all_entry = f'"{class_name}"'

        if not target_file.exists():
            target_file.write_text(f"{import_line}\n\n__all__ = [{all_entry}]\n", encoding="utf-8")
            console.success(f"created: {target_file}")
            return

        content = target_file.read_text(encoding="utf-8")
        if import_line in content:
            return  # already registered

        raw_lines = [line for line in content.splitlines() if line.strip()]
        import_lines = [
            line for line in raw_lines if line.startswith("from .") or line.startswith("import ")
        ]
        other_lines = [
            line
            for line in raw_lines
            if not (line.startswith("from .") or line.startswith("import "))
            and not line.strip().startswith("__all__")
        ]
        all_lines = [line for line in raw_lines if line.strip().startswith("__all__")]

        if import_line not in import_lines:
            import_lines.append(import_line)
        import_lines.sort()

        if all_lines:
            all_line = all_lines[0].rstrip()
            if all_line.endswith("]"):
                if all_entry not in all_line:
                    stripped = all_line[:-1].rstrip()
                    if stripped.endswith("["):
                        all_line = f"{stripped}{all_entry}]"
                    else:
                        all_line = f"{stripped}, {all_entry}]"
        else:
            all_line = f"__all__ = [{all_entry}]"

        parts = []
        if import_lines:
            parts.append("\n".join(import_lines))
        if other_lines:
            parts.append("\n".join(other_lines))
        parts.append(all_line)

        target_file.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
        console.success(f"updated: {target_file}")

    elif reg_type == "marker":
        # Strategy 2: marker comment insertion
        if not marker or not line_template:
            return

        # Render target line (e.g. app.include_router({{name_lower}}_router) -> app.include_router(users_router))
        target_line = make_env().from_string(line_template).render(context)

        if not target_file.exists():
            # Create file with marker
            target_file.write_text(f"{marker}\n{target_line}\n", encoding="utf-8")
            console.success(f"created: {target_file}")
            return

        content = target_file.read_text(encoding="utf-8")
        if target_line in content:
            return  # already registered

        if marker not in content:
            # Fallback append if marker is missing
            target_file.write_text(content + f"\n{target_line}\n", encoding="utf-8")
            console.success(f"updated: {target_file}")
            return

        lines = content.splitlines()
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if marker in line:
                new_lines.append(target_line)

        target_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        console.success(f"updated: {target_file}")
