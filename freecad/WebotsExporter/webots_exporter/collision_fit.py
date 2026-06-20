import math
from typing import Optional

from .datamodel import WbBoundingObject, WbVec3, BoundingKind


def _fit_box(dx: float, dy: float, dz: float, offset: Optional[WbVec3] = None) -> WbBoundingObject:
    if offset is None:
        offset = WbVec3()
    return WbBoundingObject(
        kind=BoundingKind.BOX,
        size=WbVec3(dx, dy, dz),
        local_offset=offset,
    )


def _try_fit_cylinder(
    diameter: float, height: float, offset: Optional[WbVec3] = None, tolerance: float = 0.15
) -> Optional[WbBoundingObject]:
    if offset is None:
        offset = WbVec3()
    if diameter <= 0 or height <= 0:
        return None
    aspect = height / diameter
    if abs(aspect - 1.0) > tolerance and abs(aspect - 2.0) > tolerance:
        return None
    return WbBoundingObject(
        kind=BoundingKind.CYLINDER,
        radius=diameter / 2.0,
        height=height,
        local_offset=offset,
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

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    center_z = (min_z + max_z) / 2.0
    offset = WbVec3(center_x, center_y, center_z)

    if prefer_cylinder:
        diam = max(dx, dy)
        cyl = _try_fit_cylinder(diam, dz, offset)
        if cyl is not None:
            return cyl

    return _fit_box(dx, dy, dz, offset)


def decimate_mesh(
    source_mesh: "Any", reduction: float = 0.1
) -> Optional["Any"]:
    try:
        import FreeCAD
        Mesh = FreeCAD.Mesh
        from PySide import QtCore
        try:
            decimated = Mesh.Mesh(source_mesh)
            num_points = getattr(source_mesh, "CountPoints", None)
            if num_points is None:
                if hasattr(source_mesh, "countPoints"):
                    num_points = source_mesh.countPoints()
                else:
                    num_points = len(getattr(source_mesh, "Points", []))
            decimated.decimate(int(num_points * reduction))
            return decimated
        except Exception:
            return None
    except ImportError:
        return None
