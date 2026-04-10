import click

from flasktool.utils import _name_parts, _write_file, _write_service_init


# =====================================================================
# Template
# =====================================================================

def _model_template(name_lower: str, name_title: str) -> str:
    return f"""\
from app import db


class {name_title}(db.Model):
    __tablename__ = "{name_lower}s"

    id         = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return {{
            "id": self.id,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
        }}
"""


# =====================================================================
# Command
# =====================================================================

@click.command(name="make:model")
@click.argument("name")
def make_model(name: str) -> None:
    """Generate a new SQLAlchemy model file in app/model/."""

    name_lower, name_title = _name_parts(name)
    model_dir = "./app/model"

    click.echo(f"\nScaffolding model '{name_title}' ...")

    _write_file(f"{model_dir}/{name_lower}.py", _model_template(name_lower, name_title))
    _write_service_init(model_dir, name_lower, name_title)

    click.echo(f"\nDone. Model '{name_title}' created in {model_dir}/")
