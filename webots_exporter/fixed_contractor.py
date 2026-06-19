from typing import Optional

from .graph_parser import AssemblyGraphParser


class _UnionFind:
    def __init__(self, n: int):
        self._parent = list(range(n))
        self._rank = [0] * n

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self._rank[rx] < self._rank[ry]:
            self._parent[rx] = ry
        elif self._rank[rx] > self._rank[ry]:
            self._parent[ry] = rx
        else:
            self._parent[ry] = rx
            self._rank[rx] += 1

    def connected(self, x: int, y: int) -> bool:
        return self.find(x) == self.find(y)


class FixedJointContractor:
    FIXED_TYPES = {"Fixed"}

    def __init__(self, parser: AssemblyGraphParser):
        self._parser = parser

    def contract(self) -> set[tuple[str, str]]:
        names = self._parser.part_names
        n = len(names)
        if n == 0:
            return set()

        name_to_idx = {name: i for i, name in enumerate(names)}
        uf = _UnionFind(n)

        fixed_pairs: set[tuple[str, str]] = set()
        for (a, b), jtype in self._parser.edge_types.items():
            if jtype in self.FIXED_TYPES:
                idx_a = name_to_idx.get(a)
                idx_b = name_to_idx.get(b)
                if idx_a is not None and idx_b is not None:
                    uf.union(idx_a, idx_b)
                    fixed_pairs.add((a, b) if a < b else (b, a))

        return fixed_pairs

    def get_merged_groups(self) -> dict[int, list[str]]:
        names = self._parser.part_names
        n = len(names)
        name_to_idx = {name: i for i, name in enumerate(names)}
        uf = _UnionFind(n)

        for (a, b), jtype in self._parser.edge_types.items():
            if jtype in self.FIXED_TYPES:
                idx_a = name_to_idx.get(a)
                idx_b = name_to_idx.get(b)
                if idx_a is not None and idx_b is not None:
                    uf.union(idx_a, idx_b)

        groups: dict[int, list[str]] = {}
        for name in names:
            idx = name_to_idx[name]
            root = uf.find(idx)
            groups.setdefault(root, []).append(name)
        return groups
