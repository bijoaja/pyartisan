import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import click

from pyartisan import __version__, config
from pyartisan.core.exceptions import ManifestError, ManifestNotFound
from pyartisan.core.manifest import load_manifest
from pyartisan.shared.deps import find_outdated, upgrade
from pyartisan.shared.updates import check_update, fetch_tags, install_hint
from pyartisan.utils import console

upgrade_deps: Callable[[Path], bool] = upgrade


def _get_upgrader() -> Callable[[Path], bool]:
    mod = sys.modules[__name__]
    up_deps = getattr(mod, "upgrade_deps", None)
    up = getattr(mod, "upgrade", None)
    if up_deps is not upgrade and callable(up_deps):
        return up_deps
    if up is not upgrade and callable(up):
        return up
    return upgrade


def _check_python() -> tuple[bool, str]:
    version = sys.version.split()[0]
    ok = sys.version_info >= (3, 10)
    return ok, f"Python {version}" + ("" if ok else " (requires >=3.10)")


def _check_uv() -> tuple[bool, str]:
    uv_path = shutil.which("uv")
    if not uv_path:
        return True, "uv not found (optional; pip is used instead)"
    try:
        out = subprocess.run([uv_path, "--version"], capture_output=True, text=True, check=True)
        return True, out.stdout.strip()
    except Exception as e:
        return False, f"uv check failed: {e}"


def _check_pip() -> tuple[bool, str]:
    # Under `uv tool install` the tool env has no pip; uv replaces it.
    uv = shutil.which("uv")
    pip_path = shutil.which("pip") or shutil.which("pip3")
    if not pip_path:
        return (True, "pip not found (uv available)") if uv else (False, "pip not found on PATH")
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        return True, out.stdout.strip()
    except Exception as e:
        return (
            (True, "pip missing in this env (uv available)")
            if uv
            else (False, f"pip check failed: {e}")
        )


def _check_git() -> tuple[bool, str]:
    git_path = shutil.which("git")
    if not git_path:
        return False, "git not found on PATH"
    try:
        out = subprocess.run(["git", "--version"], capture_output=True, text=True, check=True)
        return True, out.stdout.strip()
    except Exception as e:
        return False, f"git check failed: {e}"


def _check_venv() -> tuple[bool, str]:
    active = os.environ.get("VIRTUAL_ENV") is not None or sys.prefix != sys.base_prefix
    if active:
        return True, f"virtual environment active ({sys.prefix})"
    return False, "no virtual environment active"


CHECKS = [
    ("Python", _check_python),
    ("Uv", _check_uv),
    ("Pip", _check_pip),
    ("Git", _check_git),
    ("Virtual Environment", _check_venv),
]


def run_checks(upgrade: bool = False, cwd: Path | None = None) -> bool:
    """Run all doctor checks, print results, return True if all pass."""
    all_ok = True
    console.success("pyartisan doctor")
    console.success("-" * 40)
    for label, check_fn in CHECKS:
        ok, detail = check_fn()
        symbol = "✔" if ok else "❌"
        console.success(f"{symbol} {label}: {detail}")
        all_ok = all_ok and ok
    console.success("-" * 40)
    console.success("All checks passed." if all_ok else "Some checks failed.")

    cache_path = config.CONFIG_DIR / "version-check.json"
    newer = check_update(
        __version__,
        cache_path,
        time.time(),
        lambda: fetch_tags(config.REPO_URL),
    )
    if newer:
        console.warn(f"pyartisan {__version__} -> {newer} available")
        console.warn(f"Run: {install_hint(newer)}")

    target_cwd = cwd or Path.cwd()
    is_project = False
    try:
        load_manifest(target_cwd)
        is_project = True
    except (ManifestNotFound, ManifestError):
        pass

    if is_project:
        outdated = find_outdated(target_cwd)
        if outdated:
            console.warn("Outdated dependencies:")
            for pkg, installed, latest in outdated:
                console.warn(f"  {pkg} {installed} -> {latest}")
            if upgrade:
                if click.confirm("Do you want to upgrade dependencies now?", default=False):
                    upgrader = _get_upgrader()
                    if upgrader(target_cwd):
                        console.success("Dependencies upgraded successfully.")
                    else:
                        console.error("Upgrade failed.")
        elif outdated is None:
            console.warn(
                "Project dependencies check skipped (no lockfile/requirements or tools unavailable)."
            )

    return all_ok
