import click

from flasktool.utils import _name_parts, _write_file, _write_service_init


# =====================================================================
# Template
# =====================================================================

def _repository_template(name_lower: str, name_title: str) -> str:
    return f"""\
from app.model.{name_lower} import {name_title}
# from app.repository.base_repository import BaseRepository  # Uncomment when available


class {name_title}Repository:

    @staticmethod
    def get_all():
        # TODO: add query filters as needed
        return {name_title}.query.all()

    @staticmethod
    def get_by_id(id):
        return {name_title}.query.get(id)

    @staticmethod
    def save(instance):
        from app import db
        db.session.add(instance)
        db.session.commit()
        return instance

    @staticmethod
    def delete(instance):
        from app import db
        db.session.delete(instance)
        db.session.commit()
"""


# =====================================================================
# Command
# =====================================================================

@click.command(name="make:repository")
@click.argument("name")
def make_repository(name: str) -> None:
    """Generate a new repository class in app/repository/."""

    name_lower, name_title = _name_parts(name)
    repo_dir = "./app/repository"

    click.echo(f"\nScaffolding '{name_title}Repository' ...")

    _write_file(
        f"{repo_dir}/{name_lower}_repository.py",
        _repository_template(name_lower, name_title),
    )
    _write_service_init(repo_dir, f"{name_lower}_repository", f"{name_title}Repository")

    click.echo(f"\nDone. Repository '{name_title}Repository' created in {repo_dir}/")
