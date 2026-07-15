from pathlib import Path

# Priority order per PRD.md section 10: Flask > FastAPI > Django
FLASK_MARKERS = ("app.py",)
FLASK_SIGNATURES = ("create_app(", "Flask(")

FASTAPI_MARKERS = ("main.py",)
FASTAPI_SIGNATURES = ("FastAPI(",)

DJANGO_MARKERS = ("manage.py", "settings.py")


def _file_contains(path: Path, needles: tuple[str, ...]) -> bool:
    try:
        text = path.read_text(errors="ignore")
    except (OSError, UnicodeDecodeError):
        return False
    return any(needle in text for needle in needles)


def _any_file_matches(root: Path, filenames: tuple[str, ...], signatures: tuple[str, ...]) -> bool:
    for filename in filenames:
        candidate = root / filename
        if candidate.exists() and _file_contains(candidate, signatures):
            return True
    return False


def detect_framework(root: Path | None = None) -> str | None:
    """Detect the web framework used by the project rooted at `root`.

    Priority: Flask > FastAPI > Django (per PRD.md section 10).
    Returns the lowercase framework name, or None if detection fails.
    """
    root = root or Path.cwd()

    if _any_file_matches(root, FLASK_MARKERS, FLASK_SIGNATURES):
        return "flask"

    if _any_file_matches(root, FASTAPI_MARKERS, FASTAPI_SIGNATURES):
        return "fastapi"

    if any((root / marker).exists() for marker in DJANGO_MARKERS):
        return "django"

    return None
