import click
import os

MODEL_DIR = "./app/model"
MODEL_FILE = "./app/model/models.py"
INIT_FILE = "./app/model/__init__.py"


@click.command(name="make:model")
@click.argument("raw_path")
@click.argument("name", required=False)
def make_model(raw_path, name):
    """
    Contoh:
        flasktool make:model User
        flasktool make:model pinecone Conversations
        flasktool make:model models/pinecone Conversations
    """

    # Case 1: hanya satu argumen → raw_path = class name
    if name is None:
        name = raw_path
        dest = MODEL_FILE

    # Case 2: raw_path adalah folder/path
    else:
        # contoh: models/pinecone → app/model/models.py
        parts = raw_path.split("/")
        file_name = parts[0]  # ambil file pertama
        dest = f"./app/model/{file_name}.py"

    class_name = name
    table_name = name.lower()

    os.makedirs(os.path.dirname(dest), exist_ok=True)

    template = f"""

class {class_name}(db.Model):
    __tablename__ = "{table_name}"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(
        db.DateTime, default=db.func.now(), onupdate=db.func.now()
    )
"""

    # pastikan file ada
    if not os.path.exists(dest):
        with open(dest, "w") as f:
            f.write("from app import db\n")

    # append model
    with open(dest, "a") as f:
        f.write(template)

    click.echo(f"✔ Model {class_name} added to: {dest}")

    # update __init__.py
    _update_init_file(file_name, class_name)
    click.echo("✔ __init__.py updated")



def _update_init_file(file_name, class_name):
    """Add import and __all__ in __init__.py"""

    os.makedirs(MODEL_DIR, exist_ok=True)

    # If file does not exist, create empty file
    if not os.path.exists(INIT_FILE):
        with open(INIT_FILE, "w") as f:
            f.write("")

    # Read file content
    with open(INIT_FILE, "r") as f:
        content = f.read()

    import_line = f"from .{file_name} import {class_name}"
    all_line = f'"{class_name}"'

    new_lines = []

    # Add import if not exists
    if import_line not in content:
        new_lines.append(import_line)

    # Update __all__
    if "__all__" in content:
        # Update existing __all__
        lines = content.splitlines()
        for idx, line in enumerate(lines):
            if line.strip().startswith("__all__"):
                if all_line not in line:
                    line = line.rstrip("]").rstrip() + f", {all_line}]"
                lines[idx] = line
        content = "\n".join(lines)
    else:
        # Add new __all__ 
        new_lines.append(f"__all__ = [{all_line}]")

    # Write back to __init__.py
    with open(INIT_FILE, "w") as f:
        if new_lines:
            f.write("\n".join(new_lines) + "\n")
        f.write(content)