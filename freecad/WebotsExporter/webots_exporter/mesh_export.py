from pathlib import Path
from typing import Any, Optional


def export_obj(
    fc_shape: Any,
    output_path: Path,
    color: Optional[tuple[float, float, float]] = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vertices: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []

    mesh = getattr(fc_shape, "Mesh", None)
    if mesh is None:
        try:
            import MeshPart
            mesh = MeshPart.meshFromShape(fc_shape)
        except Exception:
            pass

    if mesh is not None:
        pts = getattr(mesh, "Points", [])
        for p in pts:
            vertices.append((p.x * 0.001, p.y * 0.001, p.z * 0.001))
        facets = getattr(mesh, "Facets", [])
        for f in facets:
            faces.append(list(f.PointIndices))

    mtl_path = output_path.with_suffix(".mtl")
    obj_name = output_path.name
    mtl_name = mtl_path.name

    r, g, b = color or (0.8, 0.8, 0.8)

    with open(mtl_path, "w") as f:
        f.write(f"newmtl material_{obj_name}\n")
        f.write(f"Kd {r} {g} {b}\n")
        f.write("illum 1\n")

    with open(output_path, "w") as f:
        f.write(f"mtllib {mtl_name}\n")
        f.write(f"o {obj_name}\n")
        for v in vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        f.write(f"usemtl material_{obj_name}\n")
        for face in faces:
            indices = " ".join(str(i + 1) for i in face)
            f.write(f"f {indices}\n")


def export_collision_stl(
    fc_shape: Any,
    output_path: Path,
    decimate: bool = False,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mesh = getattr(fc_shape, "Mesh", None)
    if mesh is None:
        try:
            import MeshPart
            mesh = MeshPart.meshFromShape(fc_shape)
        except Exception:
            pass

    if mesh is None:
        output_path.write_text("", encoding="utf-8")
        return

    try:
        import FreeCAD
        Mesh = FreeCAD.Mesh
        stl_mesh = Mesh.Mesh(mesh)
        if decimate:
            target = max(1, int(mesh.countPoints * 0.1))
            stl_mesh.decimate(target)
        stl_mesh.write(str(output_path))
    except Exception:
        _write_fallback_stl(mesh, output_path)


def _write_fallback_stl(mesh: Any, output_path: Path) -> None:
    vertices: list[tuple[float, float, float]] = []
    pts = getattr(mesh, "Points", [])
    for p in pts:
        vertices.append((p.x * 0.001, p.y * 0.001, p.z * 0.001))
    facets = getattr(mesh, "Facets", [])
    with open(output_path, "w") as f:
        f.write("solid collision\n")
        for facet in facets:
            idx = list(facet.PointIndices)
            if len(idx) >= 3:
                a, b, c = vertices[idx[0]], vertices[idx[1]], vertices[idx[2]]
                f.write(f"  facet normal 0 0 0\n")
                f.write(f"    outer loop\n")
                f.write(f"      vertex {a[0]:.6f} {a[1]:.6f} {a[2]:.6f}\n")
                f.write(f"      vertex {b[0]:.6f} {b[1]:.6f} {b[2]:.6f}\n")
                f.write(f"      vertex {c[0]:.6f} {c[1]:.6f} {c[2]:.6f}\n")
                f.write(f"    endloop\n")
                f.write(f"  endfacet\n")
        f.write("endsolid collision\n")
