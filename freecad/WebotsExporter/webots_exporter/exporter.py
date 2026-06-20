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
        try:
            import FreeCAD as _FreeCAD
        except ImportError:
            _FreeCAD = None
        parts = self._collect_parts(fc_document)

        # --- DIAGNOSTIC: collect all useful info upfront ---
        diag_lines = ["=== ProtoExporter Diagnostic ===", ""]

        diag_lines.append("-- Collected Parts --")
        for p in parts:
            shape = getattr(p, "Shape", None)
            has_shape = shape is not None
            linked = getattr(p, "LinkedObject", None)
            linked_label = getattr(linked, "Label", None) if linked else None
            diag_lines.append(
                f"  Name={p.Name} Label={p.Label} Type={p.TypeId} "
                f"HasShape={has_shape} LinkedObject={linked_label}"
            )

        parser = self._build_graph(parts, fc_document)

        diag_lines.append("")
        diag_lines.append("-- Joints (resolved) --")
        for obj in getattr(fc_document, "Objects", []):
            if hasattr(obj, "Reference1") or obj.TypeId.startswith("Assembly::Joint"):
                if obj.TypeId == "Assembly::JointGroup":
                    continue
                parent_ref, child_ref = self._get_joint_parts(obj)
                p_name = self._find_part_label(parent_ref, parts)
                c_name = self._find_part_label(child_ref, parts)
                
                props_dump = []
                for prop in obj.PropertiesList:
                    try:
                        val = getattr(obj, prop)
                        props_dump.append(f"      {prop}: {val} (type={type(val).__name__})")
                        if hasattr(val, "Base"):
                            props_dump.append(f"        Base: {val.Base}")
                        if hasattr(val, "Rotation"):
                            props_dump.append(f"        Rotation: {val.Rotation}")
                    except Exception as e:
                        props_dump.append(f"      {prop}: ERROR {e}")
                        
                diag_lines.append(
                    f"  Joint={obj.Label} ({obj.TypeId})\n"
                    f"    ref1={parent_ref} -> '{p_name}'\n"
                    f"    ref2={child_ref} -> '{c_name}'\n"
                    + "\n".join(props_dump)
                )

        diag_lines.append("")
        diag_lines.append(f"-- Graph Names: {parser.part_names}")
        diag_lines.append(f"-- Graph Adjacency: {dict(parser.adjacency)}")

        contractor = FixedJointContractor(parser)
        contractor.contract()

        try:
            root_name = parser.infer_root()
        except Exception as e:
            diag_lines.append(f"\nERROR in infer_root: {e}")
            diag_path = self.output_dir / "export_diagnostic.txt"
            diag_path.parent.mkdir(parents=True, exist_ok=True)
            diag_path.write_text("\n".join(diag_lines), encoding="utf-8")
            raise Exception(f"{e}\n\nDiagnostic saved to:\n{diag_path}")

        builder = KinematicTreeBuilder(parser)
        root_solid = builder.build(root_name)
        diag_lines.append(f"\n-- Root: {root_name}")

        self._apply_physics(root_solid, parts)

        meshes_dir = self.output_dir / "meshes"
        meshes_dir.mkdir(parents=True, exist_ok=True)

        diag_lines.append("")
        diag_lines.append("-- Mesh Export --")
        self._export_visual_meshes_diag(root_solid, meshes_dir, parts, diag_lines)
        self._apply_collision_geometry(root_solid, parts, meshes_dir)

        proto_path = self.output_dir / f"{self.world_name}.proto"
        proto_content = self.renderer.render_proto(self.world_name, root_solid)
        proto_path.write_text(proto_content, encoding="utf-8")

        diag_lines.append("")
        diag_lines.append("-- Generated PROTO --")
        diag_lines.append(proto_content)

        diag_path = self.output_dir / "export_diagnostic.txt"
        diag_path.write_text("\n".join(diag_lines), encoding="utf-8")
        if _FreeCAD is not None:
            _FreeCAD.Console.PrintMessage(f"[ProtoExporter] Diagnostic: {diag_path}\n")

        return proto_path

    def _export_visual_meshes_diag(
        self, node: "WbSolidNode", meshes_dir: Path, parts: list[Any], diag: list[str]
    ) -> None:
        """Like _export_visual_meshes but appends diagnostic info."""
        try:
            import FreeCAD
            import Mesh
        except ImportError:
            FreeCAD = None
            Mesh = None
        for joint in node.child_joints:
            if joint.child is not None:
                self._export_visual_meshes_diag(joint.child, meshes_dir, parts, diag)

        for part in parts:
            p_name = getattr(part, "Label", "")
            if p_name == node.name:
                obj_path = meshes_dir / f"{node.name}.obj"
                try:
                    if Mesh is not None:
                        Mesh.export([part], str(obj_path))
                        diag.append(f"  Node={node.name}: exported via Mesh.export successfully")
                    else:
                        diag.append(f"  Node={node.name}: Mesh is None (test mode)")
                except Exception as e:
                    diag.append(f"  Node={node.name}: Mesh.export failed: {e}")

                existing = node.geometries[0] if node.geometries else None
                color = existing.appearance.diffuse_color if existing else (0.8, 0.8, 0.8)
                if not node.geometries:
                    from .datamodel import WbShapeGeometry, WbAppearance
                    node.geometries.append(
                        WbShapeGeometry(
                            obj_relpath=f"meshes/{node.name}.obj",
                            appearance=WbAppearance(diffuse_color=color),
                        )
                    )
                obj_size = obj_path.stat().st_size if obj_path.exists() else 0
                diag.append(f"    -> {obj_path.name}: {obj_size} bytes")
                break
        else:
            diag.append(f"  Node={node.name}: NO matching part found in parts list")

    def _export_visual_meshes(
        self, node: "WbSolidNode", meshes_dir: Path, parts: list[Any]
    ) -> None:
        import Mesh
        for joint in node.child_joints:
            if joint.child is not None:
                self._export_visual_meshes(joint.child, meshes_dir, parts)

        for part in parts:
            p_name = getattr(part, "Label", "")
            if p_name == node.name:
                obj_path = meshes_dir / f"{node.name}.obj"
                try:
                    Mesh.export([part], str(obj_path))
                except Exception:
                    pass

                existing = node.geometries[0] if node.geometries else None
                color = existing.appearance.diffuse_color if existing else (0.8, 0.8, 0.8)
                if not node.geometries:
                    from .datamodel import WbShapeGeometry, WbAppearance
                    node.geometries.append(
                        WbShapeGeometry(
                            obj_relpath=f"meshes/{node.name}.obj",
                            appearance=WbAppearance(diffuse_color=color),
                        )
                    )
                break
    def _collect_parts(self, fc_document: Any) -> list[Any]:
        assembly = None
        for obj in fc_document.Objects:
            if obj.TypeId in ("Assembly::Assembly", "Assembly::AssemblyObject"):
                assembly = obj
                break
                
        parts = []
        if assembly is not None:
            self._collect_group_parts(assembly, parts)
        else:
            for obj in fc_document.Objects:
                if obj.TypeId.startswith("Assembly::Joint") or hasattr(obj, "Reference1") or obj.TypeId == "App::DocumentObjectGroup":
                    continue
                if obj.Name in ("Origin", "X_Axis", "Y_Axis", "Z_Axis", "XY_Plane", "XZ_Plane", "YZ_Plane"):
                    continue
                if hasattr(obj, "Shape") and obj.Shape is not None and hasattr(obj, "Label"):
                    if hasattr(obj, "getParentGroup"):
                        parent = obj.getParentGroup()
                        if parent is not None and parent.TypeId in ("PartDesign::Body", "App::Part"):
                            continue
                    parts.append(obj)
        return parts

    def _collect_group_parts(self, group: Any, parts: list[Any]) -> None:
        for obj in getattr(group, "Group", []):
            if obj.TypeId.startswith("Assembly::Joint") or hasattr(obj, "Reference1"):
                continue
            if obj.Name in ("Origin", "X_Axis", "Y_Axis", "Z_Axis", "XY_Plane", "XZ_Plane", "YZ_Plane"):
                continue
            if obj.TypeId in ("App::DocumentObjectGroup", "Assembly::Assembly", "Assembly::AssemblyObject"):
                self._collect_group_parts(obj, parts)
            elif hasattr(obj, "Shape") and obj.Shape is not None:
                if obj.TypeId in ("PartDesign::Body", "App::Part", "App::Link", "Part::Feature"):
                    parts.append(obj)

    def _resolve_ref(self, ref: Any) -> Any:
        if ref is None:
            return None
        if isinstance(ref, (tuple, list)):
            if len(ref) > 0:
                return self._resolve_ref(ref[0])
            return None
        ref_str = str(ref)
        if hasattr(ref, "Name"):
            return ref
        if ref_str and not ref_str.startswith("<"):
            if "." in ref_str:
                return ref_str.split(".")[0]
            return ref_str
        return ref

    def _get_joint_parts(self, fc_joint: Any) -> tuple[Optional[Any], Optional[Any]]:
        parent = self._resolve_ref(getattr(fc_joint, "Parent", None))
        if parent is None:
            parent = self._resolve_ref(getattr(fc_joint, "Reference1", None))
            
        child = self._resolve_ref(getattr(fc_joint, "Child", None))
        if child is None:
            child = self._resolve_ref(getattr(fc_joint, "Reference2", None))
        return parent, child

    def _find_part_label(self, ref_obj: Any, parts: list[Any]) -> str:
        if ref_obj is None:
            return ""
        if isinstance(ref_obj, str):
            for part in parts:
                if getattr(part, "Name", "") == ref_obj or getattr(part, "Label", "") == ref_obj:
                    return getattr(part, "Label", "")
                if getattr(part, "TypeId", "") == "App::Link":
                    linked = getattr(part, "LinkedObject", None)
                    if linked:
                        if getattr(linked, "Name", "") == ref_obj or getattr(linked, "Label", "") == ref_obj:
                            return getattr(part, "Label", "")
            return ref_obj
            
        for part in parts:
            if part is ref_obj:
                return getattr(part, "Label", "")
        for part in parts:
            if getattr(part, "TypeId", "") == "App::Link":
                linked = getattr(part, "LinkedObject", None)
                if linked is ref_obj:
                    return getattr(part, "Label", "")
        ref_name = getattr(ref_obj, "Name", "")
        if ref_name:
            for part in parts:
                if getattr(part, "Name", "") == ref_name:
                    return getattr(part, "Label", "")
                if getattr(part, "TypeId", "") == "App::Link":
                    linked = getattr(part, "LinkedObject", None)
                    if linked and getattr(linked, "Name", "") == ref_name:
                        return getattr(part, "Label", "")
        return getattr(ref_obj, "Label", "")

    def _build_graph(self, parts: list[Any], fc_doc: Any) -> AssemblyGraphParser:
        names = [getattr(p, "Label", f"Part{i}") for i, p in enumerate(parts)]
        parser = AssemblyGraphParser(names)
        
        joints = []
        if hasattr(fc_doc, "Objects"):
            for obj in fc_doc.Objects:
                if obj.TypeId == "Assembly::JointGroup":
                    continue
                if hasattr(obj, "Reference1") or hasattr(obj, "JointType") or obj.TypeId.startswith("Assembly::Joint"):
                    joints.append(obj)
        else:
            for part in parts:
                joints.extend(getattr(part, "Joints", []) or [])
                
        seen = set()
        unique_joints = []
        for j in joints:
            if j not in seen:
                seen.add(j)
                unique_joints.append(j)
                
        for j in unique_joints:
            self._add_joint_edge(parser, j, parts)
        return parser

    def _add_joint_edge(self, parser: AssemblyGraphParser, fc_joint: Any, parts: list[Any]) -> None:
        try:
            props = dump_joint_properties(fc_joint)
        except ExporterError:
            return
        parent_ref, child_ref = self._get_joint_parts(fc_joint)
        p_name = self._find_part_label(parent_ref, parts)
        c_name = self._find_part_label(child_ref, parts)
        if p_name and c_name:
            parser.add_edge(
                p_name,
                c_name,
                props["joint_type"].value,
                anchor=props.get("anchor"),
                axis=props.get("axis"),
                name=props.get("name"),
            )

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
        try:
            import FreeCAD
            import Mesh
        except ImportError:
            FreeCAD = None
            Mesh = None
        for part in parts:
            p_name = getattr(part, "Label", "")
            if p_name == node.name:
                shape = getattr(part, "Shape", None)
                if shape is not None:
                    # Get vertices via TopoShape.tessellate
                    try:
                        vertices_list, _ = shape.tessellate(0.1)
                        if vertices_list:
                            vertices = [
                                (v.x * 0.001, v.y * 0.001, v.z * 0.001)
                                for v in vertices_list
                            ]
                            node.bounding_object = fit_bounding_object(
                                vertices, prefer_cylinder=True
                            )
                            if self.collision_strategy in (
                                "Decimated Mesh Only", "auto"
                            ):
                                coll_path = meshes_dir / f"{node.name}_collision.stl"
                                try:
                                    if Mesh is not None:
                                        Mesh.export([part], str(coll_path))
                                    if node.bounding_object.kind == BoundingKind.MESH:
                                        node.bounding_object.mesh_relpath = str(coll_path)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                break
        for joint in node.child_joints:
            if joint.child is not None:
                self._apply_collision_geometry(joint.child, parts, meshes_dir)
