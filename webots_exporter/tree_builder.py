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

                child_solid = WbSolidNode(name=neighbor)
                joint = WbJointNode(
                    joint_type=joint_type,
                    anchor=WbVec3(),
                    axis=WbAxisAngle(),
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
        "Fixed": JointType.HINGE,
        "Cylindrical": JointType.HINGE,
    }
    return mapping.get(fc_type, JointType.HINGE)
