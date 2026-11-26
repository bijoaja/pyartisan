import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from pyartisan.config import REPO_URL

# ponytail: strict X.Y.Z parser; upgrade to packaging.version if pre-release tags needed
_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_semver(tag: str) -> tuple[int, int, int] | None:
    match = _SEMVER_RE.match(tag)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def latest_version(tags: list[str]) -> str | None:
    candidates = [
        (parsed, f"{parsed[0]}.{parsed[1]}.{parsed[2]}")
        for t in tags
        if (parsed := parse_semver(t)) is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def fetch_tags(repo_url: str, timeout: float = 5.0) -> list[str]:
    try:
        res = subprocess.run(
            ["git", "ls-remote", "--tags", "--refs", repo_url],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if res.returncode != 0:
            return []
    except (subprocess.SubprocessError, OSError):
        return []

    tags: list[str] = []
    output = getattr(res, "stdout", "") or ""
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("refs/tags/"):
            tags.append(parts[1].removeprefix("refs/tags/"))
    return tags


def check_update(
    current: str,
    cache_path: Path,
    now: float,
    fetch: Callable[[], list[str]],
    ttl: float = 86400.0,
) -> str | None:
    if cache_path.is_file():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            checked_at = float(data.get("checked_at", 0))
            if 0 <= now - checked_at <= ttl:
                cached_latest = data.get("latest")
                if isinstance(cached_latest, str):
                    sem_latest = parse_semver(cached_latest)
                    sem_curr = parse_semver(current)
                    if sem_latest and sem_curr and sem_latest > sem_curr:
                        return cached_latest
                return None
        except Exception:  # nosec B110  # corrupt or unreadable cache falls back to refetching upstream
            pass

    try:
        tags = fetch()
    except Exception:
        return None

    if not tags:
        return None

    latest = latest_version(tags)
    if latest is None:
        return None

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps({"checked_at": now, "latest": latest}),
            encoding="utf-8",
        )
    except OSError:
        pass

    sem_latest = parse_semver(latest)
    sem_curr = parse_semver(current)
    if sem_latest and sem_curr and sem_latest > sem_curr:
        return latest
    return None


def install_hint(version: str) -> str:
    clean_url = REPO_URL.removesuffix(".git") if REPO_URL.endswith(".git") else REPO_URL
    clean_version = version.lstrip("v")
    return f"uv tool install --force git+{clean_url}@v{clean_version}"
