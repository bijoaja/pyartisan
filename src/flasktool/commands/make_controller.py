import click
import os
import re


@click.command()
@click.argument("name")
@click.option("--type", type=click.Choice(["view", "api", "fullstack"]), required=True)
def make_controller(name, type):
    """Generate View/API/Fullstack controller"""

    base_path = f"./app/controller/{name.lower()}"
    name_lower = name.lower()
    name_cap = name.capitalize()

    created_classes = []
    created_files = []

    # =====================================================
    # Helper: Write controller file
    # =====================================================
    def write_file(path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        created_files.append(path)
        click.echo(f"✔ Created: {path}")

    # =====================================================
    # VIEW controller
    # =====================================================
    def generate_view():
        class_name = f"View{name_cap}"
        file_name = f"view_{name_lower}_controller.py"
        dest = f"{base_path}/{file_name}"

        template = f"""from app import render_template

class {class_name}:
    @staticmethod
    def index():
        return render_template("home/index.html", name="Template Flask")
"""

        write_file(dest, template)
        created_classes.append(class_name)

    # =====================================================
    # API controller
    # =====================================================
    def generate_api():
        class_name = f"Api{name_cap}Resource"
        file_name = f"api_{name_lower}_controller.py"
        dest = f"{base_path}/{file_name}"

        template = f"""from app import Resource, Response

class {class_name}(Resource):

    def get(self):
        return Response().success(values=None, message="{class_name} works")
"""

        write_file(dest, template)
        created_classes.append(class_name)

    # =====================================================
    # Handle Type options
    # =====================================================
    if type == "view":
        generate_view()
    elif type == "api":
        generate_api()
    elif type == "fullstack":
        generate_view()
        generate_api()

    # =====================================================
    # UPDATE __init__.py
    # =====================================================
    init_path = f"{base_path}/__init__.py"

    if not os.path.exists(init_path):
        with open(init_path, "w") as f:
            f.write("")

    # read old file
    with open(init_path, "r") as f:
        old = f.read()

    # extract existing imports
    existing_imports = []
    existing_classes = []

    for line in old.splitlines():
        if line.startswith("from ."):
            existing_imports.append(line)
        if "__all__" in line:
            classes = line.replace("__all__ = [", "").replace("]", "")
            existing_classes = [x.strip().strip('"') for x in classes.split(",") if x.strip()]

    # build new imports
    new_imports = []
    for cls in created_classes:
        if cls.startswith("Api"):
            fname = f"api_{name_lower}_controller"
        else:
            fname = f"view_{name_lower}_controller"

        import_line = f"from .{fname} import {cls}"

        if import_line not in existing_imports:
            new_imports.append(import_line)

    # merge imports
    all_imports = new_imports + existing_imports

    # update __all__
    final_classes = list(dict.fromkeys(created_classes + existing_classes))
    all_line = "__all__ = [" + ", ".join(f'"{c}"' for c in final_classes) + "]"

    # write back file
    with open(init_path, "w") as f:
        f.write("\n".join(all_imports) + "\n" + all_line + "\n")

    click.echo("✔ Updated: app/controller/__init__.py")

    # =====================================================
    # UPDATE Routes.py (FIXED VERSION)
    # =====================================================
    routes_path = "./app/routes.py"

    if not os.path.exists(routes_path):
        with open(routes_path, "w") as f:
            f.write(
                "from app.controller import *\n\n"
                "# ADD ROUTES API\n"
                "# (auto-generated)\n\n"
                "# ADD ROUTES VIEW\n"
                "# (auto-generated)\n\n"
            )

    # read
    with open(routes_path, "r") as f:
        lines = f.readlines()

    # ensure import exists
    if f"from app.controller.{name.lower()}" not in "".join(lines):
        classes_import = ", ".join(created_classes)
        lines.insert(0, f"from app.controller.{name.lower()} import {classes_import}\n")

    # locate API block
    try:
        api_index = next(i for i, line in enumerate(lines) if "# ADD ROUTES API" in line)
    except StopIteration:
        lines.append("\n# ADD ROUTES API\n")
        api_index = len(lines) - 1

    # locate VIEW block
    try:
        view_index = next(i for i, line in enumerate(lines) if "# ADD ROUTES VIEW" in line)
    except StopIteration:
        lines.append("\n# ADD ROUTES VIEW\n")
        view_index = len(lines) - 1

    # insert API routes under API block
    insert_api = []
    for cls in created_classes:
        if cls.startswith("Api"):
            insert_api.append(f"api.add_resource({cls}, '/{name_lower}')\n")

    # insert VIEW routes under VIEW block
    insert_view = []
    for cls in created_classes:
        if cls.startswith("View"):
            insert_view.append(f"view_bp.add_url_rule('/{name_lower}', view_func={cls}.index)\n")

    # insert API block entries right after API header
    for route in reversed(insert_api):
        lines.insert(api_index + 1, route)

    # fix view_index after API insertions
    view_index = next(i for i, line in enumerate(lines) if "# ADD ROUTES VIEW" in line)

    # insert VIEW block entries
    for route in reversed(insert_view):
        lines.insert(view_index + 1, route)

    # write file
    with open(routes_path, "w") as f:
        f.writelines(lines)

    click.echo("✔ Updated: app/routes.py")

