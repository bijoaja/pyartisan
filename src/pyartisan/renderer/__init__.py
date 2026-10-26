import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from pyartisan.utils.fs import write_file


def render_stub(stub_dir: Path, dest_dir: Path, context: dict, force: bool = False) -> list[Path]:
    """Walk through stub_dir, render file names & contents via Jinja2, and write to dest_dir."""
    if not stub_dir.exists():
        raise FileNotFoundError(f"Stub directory not found: {stub_dir}")

    rendered_files = []
    # Setup Jinja environment
    env = Environment(
        loader=FileSystemLoader(str(stub_dir)),
        keep_trailing_newline=True
    )

    # Render file names and contents
    for root, _, files in os.walk(stub_dir):
        for file in files:
            # File name rendering (e.g. {{name_lower}}_controller.py.jinja -> users_controller.py)
            rel_path = Path(root).relative_to(stub_dir) / file
            rendered_rel_path_str = env.from_string(str(rel_path)).render(context)

            # Remove .jinja suffix if present
            if rendered_rel_path_str.endswith(".jinja"):
                rendered_rel_path_str = rendered_rel_path_str[:-6]

            dest_file_path = dest_dir / rendered_rel_path_str

            # Content rendering
            template = env.get_template(rel_path.as_posix())  # Jinja only accepts '/' (str() gives '\' on Windows)
            content = template.render(context)

            write_file(str(dest_file_path), content, overwrite=force)
            rendered_files.append(dest_file_path)

    return rendered_files
