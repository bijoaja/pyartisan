import os
from pathlib import Path
from typing import Any

from jinja2 import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment

from pyartisan.core.exceptions import PyArtisanError
from pyartisan.utils.fs import write_file


def make_env(**kwargs: Any) -> SandboxedEnvironment:
    # ponytail: sandboxed environment with no autoescape; generated code is python/yaml/markdown, upgrade if html added
    return SandboxedEnvironment(**kwargs)


def render_stub(stub_dir: Path, dest_dir: Path, context: dict, force: bool = False) -> list[Path]:
    """Walk through stub_dir, render file names & contents via Jinja2, and write to dest_dir."""
    if not stub_dir.exists():
        raise FileNotFoundError(f"Stub directory not found: {stub_dir}")

    env = make_env(loader=FileSystemLoader(str(stub_dir)), keep_trailing_newline=True)

    # First pass: render file paths and validate containment
    planned = []
    dest_dir_resolved = dest_dir.resolve()
    for root, _, files in os.walk(stub_dir):
        for file in files:
            rel_path = Path(root).relative_to(stub_dir) / file
            rendered_rel_path_str = env.from_string(str(rel_path)).render(context)

            if rendered_rel_path_str.endswith(".jinja"):
                rendered_rel_path_str = rendered_rel_path_str[:-6]

            dest_file_path = dest_dir / rendered_rel_path_str
            resolved_dest = dest_file_path.resolve()
            if (
                not resolved_dest.is_relative_to(dest_dir_resolved)
                or resolved_dest == dest_dir_resolved
            ):
                raise PyArtisanError(f"Rendered path escapes destination: {dest_file_path}")

            planned.append((dest_file_path, rel_path))

    # Second pass: render content and write files
    rendered_files = []
    for dest_file_path, rel_path in planned:
        template = env.get_template(rel_path.as_posix())
        content = template.render(context)
        write_file(str(dest_file_path), content, overwrite=force)
        rendered_files.append(dest_file_path)

    return rendered_files
