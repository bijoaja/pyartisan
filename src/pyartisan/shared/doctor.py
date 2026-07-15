import os
import shutil
import subprocess
import sys

from pyartisan.utils import console


def _check_python() -> tuple[bool, str]:
    version = sys.version.split()[0]
    ok = sys.version_info >= (3, 10)
    return ok, f"Python {version}" + ("" if ok else " (requires >=3.10)")


def _check_pip() -> tuple[bool, str]:
    pip_path = shutil.which("pip") or shutil.which("pip3")
    if not pip_path:
        return False, "pip not found on PATH"
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True, text=True, check=True,
        )
        return True, out.stdout.strip()
    except Exception as e:
        return False, f"pip check failed: {e}"


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
    ("Pip", _check_pip),
    ("Git", _check_git),
    ("Virtual Environment", _check_venv),
]


def run_checks() -> bool:
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
    return all_ok
