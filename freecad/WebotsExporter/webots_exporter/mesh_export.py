from pathlib import Path
from typing import Any, Optional


def get_outer_shell_shape(fc_shape: Any) -> Any:
    if fc_shape is not None:
        try:
            import Part
            if hasattr(fc_shape, "Solids") and fc_shape.Solids:
                outer_shells = []
                for s in fc_shape.Solids:
                    if s.Shells:
                        outer_shells.append(s.Shells[0])
                if outer_shells:
                    return Part.makeCompound(outer_shells)
            elif hasattr(fc_shape, "Shells") and fc_shape.Shells:
                return fc_shape.Shells[0]
        except Exception:
            pass
    return fc_shape


def export_obj(
    fc_part: Any,
    output_path: Path,
    color: Optional[tuple[float, float, float]] = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vertices: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []

    actual_part = fc_part
    if hasattr(fc_part, "TypeId") and isinstance(fc_part.TypeId, str) and "Link" in fc_part.TypeId:
        actual_part = getattr(fc_part, "LinkedObject", fc_part) or fc_part
    
    fc_shape = getattr(actual_part, "Shape", actual_part)
    fc_shape = get_outer_shell_shape(fc_shape)

    mesh = getattr(fc_shape, "Mesh", None)
    if mesh is None and fc_shape is not None:
        try:
            import MeshPart
            # Use very fine deflection for highest visual quality
            mesh = MeshPart.meshFromShape(Shape=fc_shape, LinearDeflection=0.05, AngularDeflection=0.15)
        except Exception:
            pass

    if mesh is not None:
        num_points = getattr(mesh, "CountPoints", None)
        if not isinstance(num_points, int):
            if hasattr(mesh, "countPoints"):
                num_points = mesh.countPoints()
            else:
                num_points = len(getattr(mesh, "Points", []))
                
        if num_points > 0:
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
            return

    # Fallback to FreeCAD native export for complex types like App::Link or App::Part
    try:
        import FreeCAD
        import Mesh
        exported = False
        if fc_shape is not None:
            try:
                Mesh.export([fc_shape], str(output_path))
                exported = True
            except Exception:
                pass
        if not exported:
            Mesh.export([fc_part], str(output_path))
    except Exception as e:
        print(f"Fallback export failed: {e}")


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
            stl_mesh.decimate(1.0, 0.95)
            
        mat = FreeCAD.Matrix()
        mat.scale(0.001, 0.001, 0.001)
        stl_mesh.transformGeometry(mat)
        
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
