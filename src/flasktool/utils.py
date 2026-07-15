from pyartisan.utils.naming import name_parts as _name_parts
from pyartisan.utils.fs import (
    write_file as _write_file,
    write_controller_init as _write_controller_init,
    write_service_init as _write_service_init,
)

# =====================================================================
# Shared service templates (used by make_controller and make_service)
# Flask-specific, so they stay here rather than in pyartisan.utils.
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
