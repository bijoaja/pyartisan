import json
import re
import shutil
import subprocess
from pathlib import Path

from pyartisan.core.engine import _find_project_venv, _venv_python

Outdated = tuple[str, str, str]

# ponytail: simple package name and version matching; upgrade regex if uv changes format
_UV_UPDATE_RE = re.compile(r"Update\s+([\w.\-]+)\s+v([^\s]+)\s+->\s+v([^\s]+)")


def parse_uv_updates(output: str) -> list[Outdated]:
    return [(match[0], match[1], match[2]) for match in _UV_UPDATE_RE.findall(output)]


def parse_pip_outdated(json_text: str) -> list[Outdated]:
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(data, list):
        return []

    results: list[Outdated] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        version = item.get("version")
        latest = item.get("latest_version")
        if isinstance(name, str) and isinstance(version, str) and isinstance(latest, str):
            results.append((name, version, latest))
    return results


def _find_requirements_file(cwd: Path) -> Path | None:
    req = cwd / "requirements.txt"
    if req.exists():
        return req
    try:
        matches = sorted(cwd.glob("requirements*.txt"))
        return matches[0] if matches else None
    except OSError:
        return None


def _has_requirements(cwd: Path) -> bool:
    return _find_requirements_file(cwd) is not None


def find_outdated(cwd: Path) -> list[Outdated] | None:
    try:
        if (cwd / "uv.lock").exists() and shutil.which("uv"):
            res = subprocess.run(
                ["uv", "lock", "--upgrade", "--dry-run"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30.0,
            )
            if res.returncode != 0:
                return None
            output = (res.stdout or "") + "\n" + (res.stderr or "")
            return parse_uv_updates(output)

        if _has_requirements(cwd):
            venv = _find_project_venv(cwd)
            if not venv:
                return None
            python_bin = _venv_python(venv)
            res = subprocess.run(
                [str(python_bin), "-m", "pip", "list", "--outdated", "--format=json"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30.0,
            )  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit - argv list, fixed binary, shell=False
            if res.returncode != 0:
                return None
            return parse_pip_outdated(res.stdout or "")

        return None
    except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError):
        return None


def upgrade(cwd: Path) -> bool:
    try:
        if (cwd / "uv.lock").exists() and shutil.which("uv"):
            res1 = subprocess.run(
                ["uv", "lock", "--upgrade"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30.0,
            )
            if res1.returncode != 0:
                return False
            res2 = subprocess.run(
                ["uv", "sync"],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30.0,
            )
            return res2.returncode == 0

        req_file = _find_requirements_file(cwd)
        if req_file is not None:
            venv = _find_project_venv(cwd)
            if not venv:
                return False
            python_bin = _venv_python(venv)
            res = subprocess.run(
                [str(python_bin), "-m", "pip", "install", "-U", "-r", req_file.name],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30.0,
            )  # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-audit - argv list, fixed binary, shell=False
            return res.returncode == 0

        return False
    except (subprocess.SubprocessError, subprocess.TimeoutExpired, OSError):
        return False
