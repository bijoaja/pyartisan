import click
import os


def _name_parts(name: str) -> tuple[str, str]:
    """Return (name_lower, name_title) from any user input.

    Examples:
        'blog'      -> ('blog', 'Blog')
        'blog_post' -> ('blog_post', 'BlogPost')
        'blog-post' -> ('blog_post', 'BlogPost')
    """
    name_lower = name.lower().replace("-", "_")
    name_title = "".join(w.capitalize() for w in name_lower.split("_"))
    return name_lower, name_title


def _write_file(path: str, content: str) -> None:
    """Write file only if it does not already exist. Creates parent dirs."""
    if os.path.exists(path):
        click.echo(f"  skipped (already exists): {path}")
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    click.echo(f"  created: {path}")


def _write_controller_init(dir_path: str, file_stem: str, class_name: str) -> None:
    """Write a simple relative-import __init__.py for a single-controller feature dir."""
    content = (
        f"from .{file_stem} import {class_name}\n\n"
        f'__all__ = ["{class_name}"]\n'
    )
    _write_file(os.path.join(dir_path, "__init__.py"), content)


def _write_service_init(dir_path: str, file_stem: str, class_name: str) -> None:
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
        with open(init_path, "w") as f:
            f.write(f"{import_line}\n\n__all__ = [{all_entry}]\n")
        click.echo(f"  created: {init_path}")
        return

    with open(init_path, "r") as f:
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
        new_lines.append(f'\n__all__ = [{all_entry}]')

    with open(init_path, "w") as f:
        f.write("\n".join(new_lines) + "\n")

    click.echo(f"  updated: {init_path}")
