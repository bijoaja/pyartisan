class PyArtisanError(Exception):
    """Base exception for all PyArtisan errors."""


class FrameworkNotDetected(PyArtisanError):
    """Raised when no supported framework can be detected in the current directory."""


class PluginNotFound(PyArtisanError):
    """Raised when a requested framework plugin is not registered."""


class ConfigError(PyArtisanError):
    """Raised on invalid or unreadable config.toml content."""
