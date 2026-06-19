from pathlib import Path
from typing import Any, Optional

from .datamodel import WbSolidNode, WbVec3, WbAxisAngle, WbBoundingObject, BoundingKind
from .graph_parser import AssemblyGraphParser
from .tree_builder import KinematicTreeBuilder
from .physics import PhysicsCalculator
from .joint_introspect import dump_joint_properties
from .fixed_contractor import FixedJointContractor
from .collision_fit import fit_bounding_object
from .mesh_export import export_obj, export_collision_stl
from .render import WbtRenderer
from .exceptions import ExporterError

CollisionStrategy = str


class WebotsExporter:
    def __init__(
        self,
        output_dir: Path,
        world_name: str = "assembly_export",
        collision_strategy: CollisionStrategy = "auto",
    ):
        self.output_dir = output_dir
        self.world_name = world_name
        self.collision_strategy = collision_strategy
        self.renderer = WbtRenderer()

    def run(self, fc_document: Any) -> Path:
        parts = self._collect_parts(fc_document)
        parser = self._build_graph(parts)

        contractor = FixedJointContractor(parser)
        contractor.contract()

        root_name = parser.infer_root()
        builder = KinematicTreeBuilder(parser)
        root_solid = builder.build(root_name)

        self._apply_physics(root_solid, parts)

        meshes_dir = self.output_dir / "meshes"
        meshes_dir.mkdir(parents=True, exist_ok=True)
        self._export_visual_meshes(root_solid, meshes_dir, parts)
        self._apply_collision_geometry(root_solid, parts, meshes_dir)

        wbt_path = self.output_dir / f"{self.world_name}.wbt"
        wbt_content = self.renderer.render_world(self.world_name, root_solid)
        wbt_path.write_text(wbt_content, encoding="utf-8")
        return wbt_path

    def _collect_parts(self, fc_doc: Any) -> list[Any]:
        return []

    def _build_graph(self, parts: list[Any]) -> AssemblyGraphParser:
        names = [getattr(p, "Label", f"Part{i}") for i, p in enumerate(parts)]
        parser = AssemblyGraphParser(names)
        for i, part in enumerate(parts):
            joints = getattr(part, "Joints", []) or []
            for j in joints:
                self._add_joint_edge(parser, j)
        return parser

    def _add_joint_edge(self, parser: AssemblyGraphParser, fc_joint: Any) -> None:
        try:
            props = dump_joint_properties(fc_joint)
        except ExporterError:
            return
        parent_ref = getattr(fc_joint, "Parent", None)
        child_ref = getattr(fc_joint, "Child", None)
        p_name = getattr(parent_ref, "Label", "") if parent_ref else ""
        c_name = getattr(child_ref, "Label", "") if child_ref else ""
        if p_name and c_name:
            parser.add_edge(p_name, c_name, props["joint_type"].value)

    def _apply_physics(self, node: WbSolidNode, parts: list[Any]) -> None:
        calc = PhysicsCalculator()
        for part in parts:
            p_name = getattr(part, "Label", "")
            if p_name == node.name:
                shape = getattr(part, "Shape", None)
                if shape is not None:
                    physics = calc.compute(shape)
                    if physics is not None:
                        node.physics = physics
                break
        for joint in node.child_joints:
            if joint.child is not None:
                self._apply_physics(joint.child, parts)

    def _export_visual_meshes(
        self, node: WbSolidNode, meshes_dir: Path, parts: list[Any]
    ) -> None:
        for joint in node.child_joints:
            if joint.child is not None:
                self._export_visual_meshes(joint.child, meshes_dir, parts)

        for part in parts:
            p_name = getattr(part, "Label", "")
            if p_name == node.name:
                shape = getattr(part, "Shape", None)
                if shape is not None:
                    obj_path = meshes_dir / f"{node.name}.obj"
                    existing = node.geometries[0] if node.geometries else None
                    color = existing.appearance.diffuse_color if existing else (0.8, 0.8, 0.8)
                    export_obj(shape, obj_path, color=color)
                    if not node.geometries:
                        from .datamodel import WbShapeGeometry, WbAppearance
                        node.geometries.append(
                            WbShapeGeometry(
                                obj_relpath=f"meshes/{node.name}.obj",
                                appearance=WbAppearance(diffuse_color=color),
                            )
                        )
                break

    def _apply_collision_geometry(
        self, node: WbSolidNode, parts: list[Any], meshes_dir: Path
    ) -> None:
        for part in parts:
            p_name = getattr(part, "Label", "")
            if p_name == node.name:
                shape = getattr(part, "Shape", None)
                if shape is not None:
                    mesh = getattr(shape, "Mesh", None)
                    if mesh is not None:
                        pts = getattr(mesh, "Points", [])
                        if pts:
                            vertices = [(p.x, p.y, p.z) for p in pts]
                            node.bounding_object = fit_bounding_object(
                                vertices, prefer_cylinder=True
                            )
                            if self.collision_strategy in (
                                "Decimated Mesh Only", "auto"
                            ):
                                coll_path = meshes_dir / f"{node.name}_collision.stl"
                                export_collision_stl(
                                    shape, coll_path, decimate=True
                                )
                                if node.bounding_object.kind == BoundingKind.MESH:
                                    node.bounding_object.mesh_relpath = str(coll_path)
                break
        for joint in node.child_joints:
            if joint.child is not None:
                self._apply_collision_geometry(joint.child, parts, meshes_dir)
