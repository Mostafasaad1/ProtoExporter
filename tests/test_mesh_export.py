import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from webots_exporter.mesh_export import (
    export_collision_stl,
    export_obj,
    get_mesh_deflection,
    quality_to_deflection,
)


def test_quality_to_deflection():
    l100, a100 = quality_to_deflection(100.0)
    assert l100 == 0.005
    assert a100 == 0.02

    l50, a50 = quality_to_deflection(50.0)
    assert l50 == 0.02
    assert a50 == 0.1

    l1, a1 = quality_to_deflection(1.0)
    assert l1 == 0.5
    assert a1 == 1.0


def test_export_obj_with_faces(tmp_path):
    mock_vert1 = MagicMock(x=0.0, y=0.0, z=0.0)
    mock_vert2 = MagicMock(x=10.0, y=0.0, z=0.0)
    mock_vert3 = MagicMock(x=0.0, y=10.0, z=0.0)

    mock_face = MagicMock()
    mock_face.tessellate.return_value = (
        [mock_vert1, mock_vert2, mock_vert3],
        [(0, 1, 2)]
    )

    mock_part = MagicMock()
    mock_part.Shape.Faces = [mock_face]
    mock_part.ViewObject.ShapeColor = (0.8, 0.2, 0.2)
    mock_part.ViewObject.DiffuseColor = [(0.8, 0.2, 0.2)]

    output_obj = tmp_path / "test_part.obj"
    export_obj(mock_part, output_obj, linear_deflection=0.01, angular_deflection=0.05)

    assert output_obj.exists()
    obj_content = output_obj.read_text()
    assert "mtllib test_part.mtl" in obj_content
    assert "v 0.000000 0.000000 0.000000" in obj_content
    assert "vn " in obj_content
    assert "f 1//1 2//2 3//3" in obj_content

    mtl_path = tmp_path / "test_part.mtl"
    assert mtl_path.exists()
    mtl_content = mtl_path.read_text()
    assert "newmtl material_0.800_0.200_0.200" in mtl_content

    mock_face.tessellate.assert_called_with(0.01, 0.05)


def test_export_collision_stl(tmp_path):
    mock_shape = MagicMock(Mesh=None)
    output_stl = tmp_path / "collision.stl"

    mock_mesh = MagicMock()
    mock_pt1 = MagicMock(x=0.0, y=0.0, z=0.0)
    mock_pt2 = MagicMock(x=10.0, y=0.0, z=0.0)
    mock_pt3 = MagicMock(x=0.0, y=10.0, z=0.0)
    mock_facet = MagicMock(PointIndices=(0, 1, 2))
    mock_mesh.Points = [mock_pt1, mock_pt2, mock_pt3]
    mock_mesh.Facets = [mock_facet]

    mock_mesh_part = MagicMock()
    mock_mesh_part.meshFromShape.return_value = mock_mesh

    with patch.dict("sys.modules", {"MeshPart": mock_mesh_part}):
        export_collision_stl(mock_shape, output_stl, linear_deflection=0.01, angular_deflection=0.05)

    assert output_stl.exists()
    mock_mesh_part.meshFromShape.assert_called_with(
        Shape=mock_shape,
        LinearDeflection=0.01,
        AngularDeflection=0.05,
        Relative=False
    )
