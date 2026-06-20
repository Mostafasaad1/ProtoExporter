from collections import deque
from typing import Optional

from .datamodel import WbSolidNode, WbJointNode, WbVec3, WbAxisAngle, JointType
from .graph_parser import AssemblyGraphParser


class KinematicTreeBuilder:
    def __init__(self, parser: AssemblyGraphParser):
        self._parser = parser

    def build(self, root_name: str) -> WbSolidNode:
        visited: set[str] = set()
        queue: deque[tuple[str, WbSolidNode]] = deque()

        root = WbSolidNode(name=root_name)
        visited.add(root_name)
        queue.append((root_name, root))

        while queue:
            part_name, parent_solid = queue.popleft()
            for neighbor in self._parser.adjacency.get(part_name, set()):
                if neighbor in visited:
                    continue
                visited.add(neighbor)

                edge_key = (part_name, neighbor)
                joint_type_str = self._parser.edge_types.get(edge_key, "Revolute")
                joint_type = _map_joint_type(joint_type_str)

                props = self._parser.edge_properties.get(edge_key, {})
                anchor = props.get("anchor") or WbVec3()
                axis = props.get("axis") or WbVec3()
                joint_name = props.get("name") or ""

                min_stop_rot = props.get("min_stop_rot", 0.0)
                max_stop_rot = props.get("max_stop_rot", 0.0)
                min_stop_trans = props.get("min_stop_trans", 0.0)
                max_stop_trans = props.get("max_stop_trans", 0.0)

                min_stop = 0.0
                max_stop = 0.0
                if joint_type == JointType.HINGE:
                    min_stop = min_stop_rot
                    max_stop = max_stop_rot
                elif joint_type == JointType.SLIDER:
                    min_stop = min_stop_trans
                    max_stop = max_stop_trans

                child_solid = WbSolidNode(name=neighbor)
                joint = WbJointNode(
                    joint_type=joint_type,
                    name=joint_name,
                    anchor=anchor,
                    axis=axis,
                    min_stop=min_stop,
                    max_stop=max_stop,
                    min_stop_rot=min_stop_rot,
                    max_stop_rot=max_stop_rot,
                    min_stop_trans=min_stop_trans,
                    max_stop_trans=max_stop_trans,
                    child=child_solid,
                )
                parent_solid.child_joints.append(joint)
                queue.append((neighbor, child_solid))

        return root


def _map_joint_type(fc_type: str) -> JointType:
    mapping = {
        "Revolute": JointType.HINGE,
        "Slider": JointType.SLIDER,
        "Ball": JointType.BALL,
        "Spherical": JointType.BALL,
        "Fixed": JointType.FIXED,
        "Cylindrical": JointType.CYLINDRICAL,
        "Screw": JointType.SLIDER,
        "Hinge": JointType.HINGE,
    }
    return mapping.get(fc_type, JointType.HINGE)
