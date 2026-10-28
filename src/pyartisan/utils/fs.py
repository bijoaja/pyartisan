import os
import shutil

from pyartisan.utils import console


def write_file(path: str, content: str, overwrite: bool = False) -> None:
    """Write file, creating parent dirs. Skips existing files unless overwrite=True."""
    if os.path.exists(path) and not overwrite:
        console.warn(f"skipped (already exists): {path}")
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    console.success(f"created: {path}")


def copy_file(src: str, dst: str, skip_if_exists: bool = True) -> bool:
    """Copy `src` to `dst`. Returns False (skip) if dst exists and skip_if_exists=True."""
    if skip_if_exists and os.path.exists(dst):
        console.warn(f"skipped (already exists): {dst}")
        return False
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    shutil.copyfile(src, dst)
    console.success(f"created: {dst}")
    return True


def write_controller_init(dir_path: str, file_stem: str, class_name: str) -> None:
    """Write a simple relative-import __init__.py for a single-controller feature dir."""
    content = f'from .{file_stem} import {class_name}\n\n__all__ = ["{class_name}"]\n'
    write_file(os.path.join(dir_path, "__init__.py"), content)


def write_service_init(dir_path: str, file_stem: str, class_name: str) -> None:
    """Write (or append to) a shared __init__.py using simple relative imports.

    Because multiple classes can live under one directory (e.g. app/service/api/v1/
    may hold BlogApiService and UserApiService), this function appends a new import
    line when the file already exists rather than overwriting it.
    """
    os.makedirs(dir_path, exist_ok=True)
    init_path = os.path.join(dir_path, "__init__.py")
    import_line = f"from .{file_stem} import {class_name}"
    all_entry = f'"{class_name}"'

    if not os.path.exists(init_path):
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(f"{import_line}\n\n__all__ = [{all_entry}]\n")
        console.success(f"created: {init_path}")
        return

    with open(init_path, encoding="utf-8") as f:
        content = f.read()

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

    with open(init_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")

    console.success(f"updated: {init_path}")
