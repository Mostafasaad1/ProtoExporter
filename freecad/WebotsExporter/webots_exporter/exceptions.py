class ExporterError(Exception):
    """Base exception for all exporter errors."""


class OverconstrainedGraphError(ExporterError):
    """Raised when the constraint graph has unresolvable cycles."""


class MissingRootError(ExporterError):
    """Raised when no grounded root can be inferred in the assembly."""


class JointParsingError(ExporterError):
    """Raised when a FreeCAD joint cannot be introspected."""


class PhysicsError(ExporterError):
    """Raised when mass or COM cannot be computed."""


class RenderingError(ExporterError):
    """Raised when Jinja2 template rendering fails."""
