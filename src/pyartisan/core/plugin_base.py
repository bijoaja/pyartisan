from abc import ABC, abstractmethod
from pathlib import Path

import click


class FrameworkPlugin(ABC):
    """Contract every framework module (flasktool, fastapitool, ...) must implement."""

    name: str  # e.g. "flask", "fastapi"

    @staticmethod
    @abstractmethod
    def detect(path: Path) -> bool:
        """Return True if `path` looks like a project of this framework."""

    @abstractmethod
    def build_cli(self) -> click.Group:
        """Return a click.Group exposing this framework's make:* / serve / build commands."""
