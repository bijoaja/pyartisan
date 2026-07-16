class PyArtisanError(Exception):
    """Base exception for all PyArtisan errors."""


class FrameworkNotDetected(PyArtisanError):
    """Raised when no supported framework can be detected in the current directory."""


class PluginNotFound(PyArtisanError):
    """Raised when a requested framework plugin is not registered."""


class ConfigError(PyArtisanError):
    """Raised on invalid or unreadable config.toml content."""


class ManifestNotFound(PyArtisanError):
    """Raised when .pyartisan/manifest.yaml cannot be found in cwd."""


class ManifestError(PyArtisanError):
    """Raised when manifest.yaml is invalid or has structural errors."""


class GeneratorNotSupported(PyArtisanError):
    """Raised when the requested generator is not supported by the template."""


class TemplateNotFound(PyArtisanError):
    """Raised when no git repository URL is registered for the requested framework."""
