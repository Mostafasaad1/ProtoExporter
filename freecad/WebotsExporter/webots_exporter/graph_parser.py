from typing import Any, Optional
from collections import defaultdict

from .exceptions import MissingRootError

SENSOR_PREFIX_MAP = {
    "camera_": "Camera",
    "lidar_": "Lidar",
    "gps_": "Gps",
    "imu_": "InertialUnit"
}


def parse_sensor_type(part_name: str) -> Optional[str]:
    lower_name = part_name.lower()
    for prefix, webots_type in SENSOR_PREFIX_MAP.items():
        if lower_name.startswith(prefix):
            return webots_type
    return None



class AssemblyGraphParser:
    def __init__(self, part_names: list[str]):
        self._part_names = list(part_names)
        self.adjacency: dict[str, set[str]] = defaultdict(set)
        self.undirected_adjacency: dict[str, set[str]] = defaultdict(set)
        self.edge_types: dict[tuple[str, str], str] = {}
        self.edge_properties: dict[tuple[str, str], dict[str, Any]] = {}

    def add_edge(
        self,
        parent: str,
        child: str,
        joint_type: str,
        anchor: Optional[Any] = None,
        axis: Optional[Any] = None,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.adjacency[parent].add(child)
        self.undirected_adjacency[parent].add(child)
        self.undirected_adjacency[child].add(parent)
        self.edge_types[(parent, child)] = joint_type
        self.edge_types[(child, parent)] = joint_type

        props = {
            "joint_type": joint_type,
            "anchor": anchor,
            "axis": axis,
            "name": name,
            **kwargs,
        }
        self.edge_properties[(parent, child)] = props
        self.edge_properties[(child, parent)] = props

    def infer_root(self, fixed_parts: Optional[list[str]] = None) -> str:
        if not self._part_names:
            raise MissingRootError("No parts in assembly graph")

        # Explicit grounded parts take highest priority.
        if fixed_parts:
            for fixed in fixed_parts:
                if fixed in self._part_names:
                    return fixed

        if len(self._part_names) == 1:
            return self._part_names[0]

        # Sanity: every part must have at least one connection.
        for n in self._part_names:
            if n not in self.undirected_adjacency or not self.undirected_adjacency[n]:
                raise MissingRootError(
                    f"Part '{n}' has no connections; cannot infer root"
                )

        # FreeCAD joints have no guaranteed Reference1=parent / Reference2=child
        # ordering — a link can appear as Reference1 in multiple joints yet still
        # not be the root.  The directed in-degree approach is therefore
        # fundamentally unreliable and is not used here.
        #
        # Reliable heuristic: in a kinematic chain the base is always a leaf
        # (undirected degree = 1).  The assembly group traversal visits the base
        # link first, so among all leaves we pick the one with the lowest index
        # in the collection order.
        undirected_degrees = {
            n: len(self.undirected_adjacency.get(n, set()))
            for n in self._part_names
        }
        order = {name: i for i, name in enumerate(self._part_names)}
        leaves = [n for n, d in undirected_degrees.items() if d == 1]

        if leaves:
            return min(leaves, key=lambda n: order[n])

        # No leaves (fully-connected or cycle): pick the node with the fewest
        # undirected connections, breaking ties by collection order.
        min_deg = min(undirected_degrees.values())
        candidates = [n for n, d in undirected_degrees.items() if d == min_deg]
        return min(candidates, key=lambda n: order[n])



    def graph_density(self) -> float:
        n = len(self._part_names)
        if n < 2:
            return 0.0
        max_edges = n * (n - 1) / 2.0
        actual = len(self.edge_types) / 2
        return actual / max_edges

    @property
    def part_names(self) -> list[str]:
        return list(self._part_names)

