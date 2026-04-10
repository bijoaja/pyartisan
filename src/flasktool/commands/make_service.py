import click

from flasktool.utils import _name_parts, _write_file, _write_service_init


# =====================================================================
# Templates
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
# Command
# =====================================================================

@click.command()
@click.argument("name")
@click.option(
    "--type", "svc_type",
    type=click.Choice(["view", "api"]),
    required=True,
    help="Service type to generate",
)
@click.option(
    "--version", default="1", show_default=True,
    help="API version number (used for --type api)",
)
def make_service(name: str, svc_type: str, version: str) -> None:
    """Generate a standalone View or API service class."""

    name_lower, name_title = _name_parts(name)
    ver = version

    click.echo(f"\nScaffolding '{name_title}Service' ({svc_type}) ...")

    if svc_type == "view":
        svc_dir = "./app/service"
        _write_file(
            f"{svc_dir}/{name_lower}_service.py",
            _view_service_template(name_lower, name_title),
        )
        _write_service_init(svc_dir, f"{name_lower}_service", f"{name_title}Service")

    elif svc_type == "api":
        svc_dir = f"./app/service/api/v{ver}"
        _write_file(
            f"{svc_dir}/{name_lower}_service.py",
            _api_service_template(name_lower, name_title),
        )
        _write_service_init(svc_dir, f"{name_lower}_service", f"{name_title}ApiService")

    click.echo(f"\nDone. Service '{name_title}' generated successfully.")
