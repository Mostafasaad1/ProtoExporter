from typing import Any, Optional
from collections import defaultdict

from .exceptions import MissingRootError


class AssemblyGraphParser:
    def __init__(self, part_names: list[str]):
        self._part_names = list(part_names)
        self.adjacency: dict[str, set[str]] = defaultdict(set)
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
    ) -> None:
        self.adjacency[parent].add(child)
        self.adjacency[child].add(parent)
        self.edge_types[(parent, child)] = joint_type
        self.edge_types[(child, parent)] = joint_type
        
        props = {
            "joint_type": joint_type,
            "anchor": anchor,
            "axis": axis,
            "name": name,
        }
        self.edge_properties[(parent, child)] = props
        self.edge_properties[(child, parent)] = props

    def infer_root(self) -> str:
        if not self._part_names:
            raise MissingRootError("No parts in assembly graph")
        if len(self._part_names) == 1:
            return self._part_names[0]
        degrees = {n: len(self.adjacency.get(n, set())) for n in self._part_names}
        for n in self._part_names:
            if degrees.get(n, 0) == 0:
                raise MissingRootError(
                    f"Part '{n}' has no connections; cannot infer root"
                )
        min_deg = min(degrees.values())
        candidates = [n for n, d in degrees.items() if d == min_deg]
        if not candidates:
            raise MissingRootError("No root candidate found in graph")
        return candidates[0]

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
