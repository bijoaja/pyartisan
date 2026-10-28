"""Validation helpers for untrusted names, paths and clone URLs."""

import os
import re
from pathlib import Path

from pyartisan.core.exceptions import PyArtisanError

NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
_CLONE_URL_RE = re.compile(r"(https://|ssh://|git@[\w.-]+:)[^\s]+")


def validate_name(value: str, what: str = "name") -> str:
    """Return value if it is a single safe path segment, else raise."""
    if not NAME_RE.fullmatch(value):
        raise PyArtisanError(f"Invalid {what}: {value!r}")
    return value


def safe_child(root: Path, *parts: str) -> Path:
    """Join parts under root; raise if the result is root or escapes it.

    Lexical check only: resolve() is deliberately not used because dev links
    point outside the registry on purpose.
    """
    base = os.path.normpath(root)
    candidate = os.path.normpath(os.path.join(root, *parts))
    if candidate == base or not Path(candidate).is_relative_to(base):
        raise PyArtisanError(f"Invalid path: {'/'.join(parts)!r}")
    return Path(candidate)


def validate_clone_url(url: str, what: str = "URL") -> str:
    """Return url if it is https://, ssh:// or scp-style git@host:, else raise."""
    if not _CLONE_URL_RE.fullmatch(url):
        raise PyArtisanError(f"Invalid {what}: {url!r}")
    return url
