# Re-export helpers from marketplace.core for backward compatibility.
# CLI commands (plugin_group and subcommands) live in
# pyartisan.cli.commands.plugin.
from pyartisan.marketplace.core import (
    _global_registry,
    _plugins_registry,
    _usage_file,
    _load_usage,
    _save_usage,
    _record_usage,
    _unrecord_usage,
    _all_usages,
    _load_hooks,
    _verify_blockchain_license,
    _resolve_plugin_version,
    _find_registry_dir,
    _version_key,
    _latest_version,
    _check_updates,
)
