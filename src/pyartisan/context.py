from dataclasses import dataclass
from pathlib import Path

from pyartisan.core.detector import detect_framework


@dataclass
class ProjectContext:
    """Resolved state for the current CLI invocation: where we are and which framework applies."""

    root: Path
    framework: str | None

    @classmethod
    def resolve(cls, explicit_framework: str | None = None, root: Path | None = None) -> "ProjectContext":
        root = root or Path.cwd()
        framework = explicit_framework or detect_framework(root)
        return cls(root=root, framework=framework)
