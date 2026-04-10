import click
import os

from flasktool.utils import (
    _name_parts,
    _write_file,
    _write_controller_init,
    _write_service_init,
)


# =====================================================================
# Template: View controller
# =====================================================================

def _view_controller_template(name_lower: str, name_title: str) -> str:
    return f"""\
from flask import render_template, redirect, url_for, request


class {name_title}Controller:

    @staticmethod
    def index():
        # TODO: call {name_title}Service.get_all()
        return render_template("{name_lower}/index.html")

    @staticmethod
    def show(id):
        # TODO: call {name_title}Service.get_by_id(id)
        return render_template("{name_lower}/show.html")

    @staticmethod
    def create():
        return render_template("{name_lower}/create.html")

    @staticmethod
    def store():
        # TODO: call {name_title}Service.create(request.form.to_dict())
        return redirect(url_for("{name_lower}.index"))

    @staticmethod
    def edit(id):
        # TODO: call {name_title}Service.get_by_id(id)
        return render_template("{name_lower}/edit.html")

    @staticmethod
    def update(id):
        # TODO: call {name_title}Service.update(id, request.form.to_dict())
        return redirect(url_for("{name_lower}.index"))

    @staticmethod
    def destroy(id):
        # TODO: call {name_title}Service.delete(id)
        return redirect(url_for("{name_lower}.index"))
"""


# =====================================================================
# Template: API controller
# =====================================================================

def _api_controller_template(name_lower: str, name_title: str, ver: str) -> str:
    return f"""\
from flask_restful import Resource
# from utils.response import Response  # Uncomment when available
# from utils.middleware import Middleware  # Uncomment to protect route


class {name_title}ApiController(Resource):

    # @Middleware.token_required
    def get(self, id=None):
        # TODO: call {name_title}ApiService.get_all() or get_by_id(id)
        return {{"success": True, "data": [], "message": "OK"}}, 200

    # @Middleware.token_required
    def post(self):
        # TODO: call {name_title}ApiService.create(request.get_json())
        return {{"success": True, "data": {{}}, "message": "Created"}}, 201

    # @Middleware.token_required
    def put(self, id):
        # TODO: call {name_title}ApiService.update(id, request.get_json())
        return {{"success": True, "data": {{}}, "message": "Updated"}}, 200

    # @Middleware.token_required
    def delete(self, id):
        # TODO: call {name_title}ApiService.delete(id)
        return {{"success": True, "data": {{}}, "message": "Deleted"}}, 200
"""


# =====================================================================
# Template: View service
# =====================================================================

def _view_service_template(name_lower: str, name_title: str) -> str:
    return f"""\
class {name_title}Service:

    @staticmethod
    def get_all():
        # TODO: use {name_title}Repository.get_all()
        return []

    @staticmethod
    def get_by_id(id):
        # TODO: use {name_title}Repository.get_by_id(id)
        return None

    @staticmethod
    def create(data: dict):
        # TODO: use {name_title}Repository.save(instance)
        pass

    @staticmethod
    def update(id, data: dict):
        # TODO: use {name_title}Repository.save(instance)
        pass

    @staticmethod
    def delete(id):
        # TODO: use {name_title}Repository.delete(instance)
        pass
"""


# =====================================================================
# Template: API service
# =====================================================================

def _api_service_template(name_lower: str, name_title: str) -> str:
    return f"""\
class {name_title}ApiService:

    @staticmethod
    def get_all():
        # TODO: use {name_title}Repository.get_all()
        return []

    @staticmethod
    def get_by_id(id):
        # TODO: use {name_title}Repository.get_by_id(id)
        return None

    @staticmethod
    def create(data: dict):
        # TODO: use {name_title}Repository.save(instance)
        pass

    @staticmethod
    def update(id, data: dict):
        # TODO: use {name_title}Repository.save(instance)
        pass

    @staticmethod
    def delete(id):
        # TODO: use {name_title}Repository.delete(instance)
        pass
"""


# =====================================================================
# Routes generators
# =====================================================================

def _view_routes_template(name_lower: str, name_title: str) -> str:
    """Generate app/routes/{name_lower}.py — Blueprint file per feature."""
    return f"""\
from flask import Blueprint
from app.controller.view.{name_lower} import {name_title}Controller

{name_lower}_bp = Blueprint("{name_lower}", __name__)

{name_lower}_bp.add_url_rule("/{name_lower}",                view_func={name_title}Controller.index,   methods=["GET"])
{name_lower}_bp.add_url_rule("/{name_lower}/create",         view_func={name_title}Controller.create,  methods=["GET"])
{name_lower}_bp.add_url_rule("/{name_lower}",                view_func={name_title}Controller.store,   methods=["POST"])
{name_lower}_bp.add_url_rule("/{name_lower}/<int:id>",       view_func={name_title}Controller.show,    methods=["GET"])
{name_lower}_bp.add_url_rule("/{name_lower}/<int:id>/edit",  view_func={name_title}Controller.edit,    methods=["GET"])
{name_lower}_bp.add_url_rule("/{name_lower}/<int:id>",       view_func={name_title}Controller.update,  methods=["PUT"])
{name_lower}_bp.add_url_rule("/{name_lower}/<int:id>",       view_func={name_title}Controller.destroy, methods=["DELETE"])
"""


def _append_api_route(name_lower: str, name_title: str, ver: str) -> None:
    """Append a resource registration to app/routes/api/v{ver}/__init__.py."""
    api_routes_dir = f"./app/routes/api/v{ver}"
    api_routes_file = f"{api_routes_dir}/__init__.py"
    import_line = (
        f"from app.controller.api.v{ver}.{name_lower} "
        f"import {name_title}ApiController"
    )
    register_block = (
        f"\n\ndef register_{name_lower}_routes(api):\n"
        f"    api.add_resource(\n"
        f"        {name_title}ApiController,\n"
        f"        \"/v{ver}/{name_lower}\",\n"
        f"        \"/v{ver}/{name_lower}/<int:id>\",\n"
        f"    )\n"
    )

    os.makedirs(api_routes_dir, exist_ok=True)

    if not os.path.exists(api_routes_file):
        with open(api_routes_file, "w") as f:
            f.write(f"# API v{ver} route registrations\n")
            f.write(f"{import_line}")
            f.write(register_block)
        click.echo(f"  created: {api_routes_file}")
        return

    with open(api_routes_file, "r") as f:
        content = f.read()

    if import_line in content:
        return  # already registered

    with open(api_routes_file, "a") as f:
        f.write(f"\n{import_line}")
        f.write(register_block)

    click.echo(f"  updated: {api_routes_file}")


# =====================================================================
# Command
# =====================================================================

@click.command()
@click.argument("name")
@click.option(
    "--type", "ctrl_type",
    type=click.Choice(["view", "api", "fullstack"]),
    required=True,
    help="Controller type to generate",
)
@click.option(
    "--version", default="1", show_default=True,
    help="API version number (used for api/fullstack types)",
)
def make_controller(name: str, ctrl_type: str, version: str) -> None:
    """Generate View / API / Fullstack controller with service layer."""

    name_lower, name_title = _name_parts(name)
    ver = version

    click.echo(f"\nScaffolding '{name_title}' ({ctrl_type}) ...")

    # ------------------------------------------------------------------
    # View layer
    # ------------------------------------------------------------------
    if ctrl_type in ("view", "fullstack"):
        # Service
        view_svc_dir = "./app/service"
        _write_file(
            f"{view_svc_dir}/{name_lower}_service.py",
            _view_service_template(name_lower, name_title),
        )
        _write_service_init(view_svc_dir, f"{name_lower}_service", f"{name_title}Service")

        # Controller
        view_ctrl_dir = f"./app/controller/view/{name_lower}"
        _write_file(
            f"{view_ctrl_dir}/{name_lower}_controller.py",
            _view_controller_template(name_lower, name_title),
        )
        _write_controller_init(view_ctrl_dir, f"{name_lower}_controller", f"{name_title}Controller")

        # Routes
        os.makedirs("./app/routes", exist_ok=True)
        _write_file(
            f"./app/routes/{name_lower}.py",
            _view_routes_template(name_lower, name_title),
        )

    # ------------------------------------------------------------------
    # API layer
    # ------------------------------------------------------------------
    if ctrl_type in ("api", "fullstack"):
        # Service
        api_svc_dir = f"./app/service/api/v{ver}"
        _write_file(
            f"{api_svc_dir}/{name_lower}_service.py",
            _api_service_template(name_lower, name_title),
        )
        _write_service_init(api_svc_dir, f"{name_lower}_service", f"{name_title}ApiService")

        # Controller
        api_ctrl_dir = f"./app/controller/api/v{ver}/{name_lower}"
        _write_file(
            f"{api_ctrl_dir}/{name_lower}_controller.py",
            _api_controller_template(name_lower, name_title, ver),
        )
        _write_controller_init(api_ctrl_dir, f"{name_lower}_controller", f"{name_title}ApiController")

        # Routes
        _append_api_route(name_lower, name_title, ver)

    click.echo(f"\nDone. Controller '{name_title}' scaffolded successfully.")
