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
            
        if fixed_parts:
            for fixed in fixed_parts:
                if fixed in self._part_names:
                    return fixed

        if len(self._part_names) == 1:
            return self._part_names[0]
            
        for n in self._part_names:
            has_connections = False
            if n in self.adjacency and self.adjacency[n]:
                has_connections = True
            else:
                for parent, children in self.adjacency.items():
                    if n in children:
                        has_connections = True
                        break
            if not has_connections:
                raise MissingRootError(
                    f"Part '{n}' has no connections; cannot infer root"
                )

        in_degrees = {n: 0 for n in self._part_names}
        for parent, children in self.adjacency.items():
            for child in children:
                if child in in_degrees:
                    in_degrees[child] += 1
                    
        roots = [n for n, in_deg in in_degrees.items() if in_deg == 0]
        if len(roots) == 1:
            return roots[0]
        if len(roots) > 1:
            out_degrees = {n: len(self.adjacency.get(n, set())) for n in roots}
            return max(roots, key=lambda n: out_degrees[n])
            
        total_degrees = {}
        for n in self._part_names:
            out_deg = len(self.adjacency.get(n, set()))
            in_deg = in_degrees.get(n, 0)
            total_degrees[n] = out_deg + in_deg
            
        min_deg = min(total_degrees.values())
        candidates = [n for n, d in total_degrees.items() if d == min_deg]
        if candidates:
            return candidates[0]
        raise MissingRootError("No root candidate found in graph")

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

