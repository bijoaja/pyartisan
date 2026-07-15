import importlib

from pyartisan.exceptions import PluginNotFound

# Static registry: framework name -> (module path, class name).
# Adding a new framework means adding one entry here, no core changes needed.
_REGISTRY = {
    "flask": ("flasktool.plugin", "FlaskPlugin"),
    "fastapi": ("fastapitool.plugin", "FastAPIPlugin"),
}


def available_frameworks() -> list[str]:
    return sorted(_REGISTRY)


def load_plugin(framework: str):
    """Lazily import and instantiate the plugin for `framework`.

    Only the requested plugin's module is imported (keeps CLI startup fast —
    other frameworks' commands, and their dependencies, never get loaded).
    """
    if framework not in _REGISTRY:
        raise PluginNotFound(
            f"No plugin registered for framework '{framework}'. "
            f"Available: {', '.join(available_frameworks())}"
        )
    module_name, cls_name = _REGISTRY[framework]
    module = importlib.import_module(module_name)
    return getattr(module, cls_name)()
