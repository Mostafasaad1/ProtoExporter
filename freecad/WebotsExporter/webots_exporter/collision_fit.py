import math
from typing import Optional

from .datamodel import WbBoundingObject, WbVec3, BoundingKind


def _fit_box(dx: float, dy: float, dz: float) -> WbBoundingObject:
    return WbBoundingObject(
        kind=BoundingKind.BOX,
        size=WbVec3(dx, dy, dz),
    )


def _try_fit_cylinder(
    diameter: float, height: float, tolerance: float = 0.15
) -> Optional[WbBoundingObject]:
    if diameter <= 0 or height <= 0:
        return None
    aspect = height / diameter
    if abs(aspect - 1.0) > tolerance and abs(aspect - 2.0) > tolerance:
        return None
    return WbBoundingObject(
        kind=BoundingKind.CYLINDER,
        radius=diameter / 2.0,
        height=height,
    )


def fit_bounding_object(
    vertices: list[tuple[float, float, float]],
    prefer_cylinder: bool = True,
) -> WbBoundingObject:
    min_x = min(v[0] for v in vertices)
    max_x = max(v[0] for v in vertices)
    min_y = min(v[1] for v in vertices)
    max_y = max(v[1] for v in vertices)
    min_z = min(v[2] for v in vertices)
    max_z = max(v[2] for v in vertices)

    dx = max_x - min_x
    dy = max_y - min_y
    dz = max_z - min_z

    if prefer_cylinder:
        diam = max(dx, dy)
        cyl = _try_fit_cylinder(diam, dz)
        if cyl is not None:
            return cyl

    return _fit_box(dx, dy, dz)


def decimate_mesh(
    source_mesh: "Any", reduction: float = 0.1
) -> Optional["Any"]:
    try:
        import FreeCAD
        Mesh = FreeCAD.Mesh
        from PySide import QtCore
        try:
            decimated = Mesh.Mesh(source_mesh)
            decimated.decimate(int(source_mesh.countPoints * reduction))
            return decimated
        except Exception:
            return None
    except ImportError:
        return None
