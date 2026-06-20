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


def is_poor_primitive_fit(shape_volume: float, primitive: WbBoundingObject) -> bool:
    """Returns True if the shape volume is less than 80% of the primitive volume."""
    if shape_volume <= 0:
        return False
    
    if primitive.kind == BoundingKind.BOX:
        prim_vol = primitive.size.x * primitive.size.y * primitive.size.z
    elif primitive.kind == BoundingKind.CYLINDER:
        prim_vol = math.pi * (primitive.radius ** 2) * primitive.height
    else:
        return False
        
    if prim_vol <= 0:
        return False
        
    prim_vol_mm3 = prim_vol * 1e9
    return (shape_volume / prim_vol_mm3) < 0.8


def compute_convex_hull_mesh(vertices: list[tuple[float, float, float]], output_path: str) -> bool:
    """Computes a convex hull using scipy and saves it as an STL file."""
    try:
        import numpy as np
        from scipy.spatial import ConvexHull
    except ImportError:
        return False
        
    if len(vertices) < 4:
        return False
        
    try:
        points = np.array(vertices)
        hull = ConvexHull(points)
        
        with open(output_path, "w") as f:
            f.write("solid convex_hull\n")
            for simplex in hull.simplices:
                pts_simplex = points[simplex]
                
                v1 = pts_simplex[1] - pts_simplex[0]
                v2 = pts_simplex[2] - pts_simplex[0]
                normal = np.cross(v1, v2)
                norm = np.linalg.norm(normal)
                if norm > 0:
                    normal = normal / norm
                else:
                    normal = np.array([0.0, 0.0, 0.0])
                    
                f.write(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
                f.write("    outer loop\n")
                for p in pts_simplex:
                    f.write(f"      vertex {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")
                f.write("    endloop\n")
                f.write("  endfacet\n")
            f.write("endsolid convex_hull\n")
        return True
    except Exception:
        return False
