import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from pyartisan.core.exceptions import ConfigError

CONFIG_DIR = Path.home() / ".pyartisan"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = {
    "theme": "default",
    "author": "",
    "license": "MIT",
    "default_framework": "flask",
    "templates": {
        "flask": "https://github.com/bijoaja/flaskiq.git",
        "fastapi": "https://github.com/bijoaja/fastiq.git",
    },
}


def _dump_toml(data: dict) -> str:
    """Minimal flat-key TOML writer — config.toml only ever holds flat string
    keys (see DEFAULT_CONFIG), so a full TOML writer dependency (tomli_w) is
    unnecessary."""
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            # Write nested table for templates map
            lines.append(f"[{key}]")
            for sub_k, sub_v in value.items():
                escaped = sub_v.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{sub_k} = "{escaped}"')
            lines.append("")
        elif isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        elif isinstance(value, bool):
            lines.append(f"{key} = {str(value).lower()}")
        else:
            lines.append(f"{key} = {value}")
    return "\n".join(lines) + "\n"


def load() -> dict:
    """Load config, creating it with defaults on first run."""
    if not CONFIG_PATH.exists():
        save(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    try:
        with open(CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Invalid config at {CONFIG_PATH}: {e}") from e

    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    return merged


def save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(_dump_toml(data), encoding="utf-8")


def reset() -> dict:
    save(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)
