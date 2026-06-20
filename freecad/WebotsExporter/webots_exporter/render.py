from pathlib import Path
from typing import Any
from jinja2 import Environment, FileSystemLoader

from .datamodel import WbSolidNode, WbJointNode, JointType
from .exceptions import RenderingError

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

JOINT_TEMPLATE_MAP = {
    JointType.HINGE: "joint_hinge.proto.j2",
    JointType.SLIDER: "joint_slider.proto.j2",
    JointType.BALL: "joint_ball.proto.j2",
}


class WbtRenderer:
    def __init__(self, template_dir: Path = TEMPLATE_DIR):
        if not template_dir.is_dir():
            raise RenderingError(f"Template directory not found: {template_dir}")
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_world(self, world_name: str, root_solid: WbSolidNode) -> str:
        template = self._env.get_template("world.wbt.j2")
        solid_text = self._render_solid(root_solid)
        return template.render(world_name=world_name, root_solid=solid_text)

    def render_proto(self, proto_name: str, root_solid: WbSolidNode) -> str:
        template = self._env.get_template("proto.j2")
        node_type = "Robot" if self._has_joints(root_solid) else "Solid"
        solid_text = self._render_solid(root_solid, is_root=True)
        return template.render(proto_name=proto_name, root_solid=solid_text, node_type=node_type)

    def _render_solid(self, node: WbSolidNode, is_root: bool = False) -> str:
        template = self._env.get_template("solid.proto.j2")
        rendered_joints = [self._render_joint(j) for j in node.child_joints]
        
        node_type = "Solid"
        if is_root and self._has_joints(node):
            node_type = "Robot"
            
        return template.render(
            node=node,
            joints=rendered_joints,
            is_root=is_root,
            node_type=node_type,
        )

    def _has_joints(self, node: WbSolidNode) -> bool:
        if node.child_joints:
            return True
        for joint in node.child_joints:
            if joint.child and self._has_joints(joint.child):
                return True
        return False

    def _render_joint(self, joint: WbJointNode) -> str:
        tmpl_name = JOINT_TEMPLATE_MAP.get(joint.joint_type)
        if tmpl_name is None:
            raise RenderingError(f"No template for joint type: {joint.joint_type}")
        template = self._env.get_template(tmpl_name)
        
        rendered_child = self._render_solid(joint.child) if joint.child else ""
        
        ctx: dict[str, Any] = {
            "joint": joint,
            "child_solid": rendered_child
        }
        return template.render(ctx)
