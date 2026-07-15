"""
Force-directed layout for the Three.js network topology visualization skill.

Ported and adapted from workspace/skills/ue5-network-viz/layout.py, which is
already engine-agnostic (pure Python, produces abstract Vector3 positions with
no engine API calls). This module keeps that algorithm — including its
centroid re-centering fix — rather than re-deriving it, per research.md §4
and spec.md FR-008 (topology layouts must render centered/scaled regardless
of source coordinate ranges). Spatial constants are rescaled from the UE5
port's centimeter-based defaults down to generic Three.js scene units (see
DEFAULT bounds/edge-length below), since this skill has no "centimeters"
convention of its own.
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from topology_model import Device, Link, Vector3


@dataclass
class LayoutNode:
    id: str
    device_role: str = "unclassified"
    position: Vector3 = field(default_factory=Vector3)
    fixed: bool = False


@dataclass
class LayoutEdge:
    source_id: str
    target_id: str
    weight: float = 1.0


@dataclass
class LayoutConfig:
    """Force-directed layout tuning, in generic Three.js scene units."""

    repulsion_strength: float = 200.0
    attraction_strength: float = 0.1
    ideal_edge_length: float = 6.0

    type_clustering_strength: float = 0.02

    max_iterations: int = 100
    cooling_factor: float = 0.95
    initial_temperature: float = 1.0
    min_temperature: float = 0.001
    convergence_threshold: float = 0.005

    # Bounds in generic scene units — sized so default procedural device
    # meshes (~1 unit) and their labels stay legible at a typical camera
    # distance, mirroring the lesson from the UE5 port's own scale bug.
    bounds_min: Vector3 = field(default_factory=lambda: Vector3(-40, -40, 0))
    bounds_max: Vector3 = field(default_factory=lambda: Vector3(40, 40, 10))


class ForceDirectedLayout:
    """Fruchterman-Reingold-style 3D force-directed layout with type clustering."""

    def __init__(self, config: Optional[LayoutConfig] = None):
        self.config = config or LayoutConfig()
        self.nodes: dict[str, LayoutNode] = {}
        self.edges: list[LayoutEdge] = []

    def add_node(
        self,
        node_id: str,
        device_role: str = "unclassified",
        position: Optional[Vector3] = None,
        fixed: bool = False,
    ) -> LayoutNode:
        if position is None:
            position = Vector3(
                random.uniform(self.config.bounds_min.x, self.config.bounds_max.x),
                random.uniform(self.config.bounds_min.y, self.config.bounds_max.y),
                random.uniform(self.config.bounds_min.z, self.config.bounds_max.z),
            )
        node = LayoutNode(id=node_id, device_role=device_role, position=position, fixed=fixed)
        self.nodes[node_id] = node
        return node

    def add_edge(self, source_id: str, target_id: str, weight: float = 1.0) -> Optional[LayoutEdge]:
        if source_id not in self.nodes or target_id not in self.nodes:
            return None
        edge = LayoutEdge(source_id, target_id, weight)
        self.edges.append(edge)
        return edge

    def _calculate_repulsion(self, node1: LayoutNode, node2: LayoutNode) -> Vector3:
        delta = node1.position - node2.position
        distance = delta.magnitude()
        if distance < 0.01:
            distance = 0.01
        force_magnitude = self.config.repulsion_strength / (distance * distance)
        return delta.normalized() * force_magnitude

    def _calculate_attraction(self, edge: LayoutEdge) -> tuple[Vector3, Vector3]:
        source = self.nodes[edge.source_id]
        target = self.nodes[edge.target_id]
        delta = target.position - source.position
        distance = delta.magnitude()
        if distance < 0.01:
            distance = 0.01
        displacement = distance - self.config.ideal_edge_length
        force_magnitude = self.config.attraction_strength * displacement * edge.weight
        direction = delta.normalized()
        return direction * force_magnitude, direction * (-force_magnitude)

    def _calculate_type_clustering(self, node1: LayoutNode, node2: LayoutNode) -> Vector3:
        if node1.device_role != node2.device_role:
            return Vector3(0, 0, 0)
        delta = node2.position - node1.position
        distance = delta.magnitude()
        if distance < 0.01:
            return Vector3(0, 0, 0)
        force_magnitude = self.config.type_clustering_strength * distance
        return delta.normalized() * force_magnitude

    def _apply_bounds(self, position: Vector3) -> Vector3:
        return Vector3(
            max(self.config.bounds_min.x, min(self.config.bounds_max.x, position.x)),
            max(self.config.bounds_min.y, min(self.config.bounds_max.y, position.y)),
            max(self.config.bounds_min.z, min(self.config.bounds_max.z, position.z)),
        )

    def run(self) -> dict[str, Vector3]:
        if len(self.nodes) == 0:
            return {}

        if len(self.nodes) == 1:
            node = next(iter(self.nodes.values()))
            node.position = Vector3(
                (self.config.bounds_min.x + self.config.bounds_max.x) / 2,
                (self.config.bounds_min.y + self.config.bounds_max.y) / 2,
                (self.config.bounds_min.z + self.config.bounds_max.z) / 2,
            )
            return {node.id: node.position}

        temperature = self.config.initial_temperature
        node_list = list(self.nodes.values())

        for _ in range(self.config.max_iterations):
            forces: dict[str, Vector3] = {n.id: Vector3() for n in node_list}

            for i, node1 in enumerate(node_list):
                for node2 in node_list[i + 1 :]:
                    repulsion = self._calculate_repulsion(node1, node2)
                    forces[node1.id] = forces[node1.id] + repulsion
                    forces[node2.id] = forces[node2.id] - repulsion

                    clustering = self._calculate_type_clustering(node1, node2)
                    forces[node1.id] = forces[node1.id] + clustering
                    forces[node2.id] = forces[node2.id] - clustering

            for edge in self.edges:
                force_source, force_target = self._calculate_attraction(edge)
                forces[edge.source_id] = forces[edge.source_id] + force_source
                forces[edge.target_id] = forces[edge.target_id] + force_target

            max_displacement = 0.0
            for node in node_list:
                if node.fixed:
                    continue
                force = forces[node.id]
                force_mag = force.magnitude()
                if force_mag > 0:
                    displacement = force.normalized() * min(force_mag, temperature)
                    node.position = self._apply_bounds(node.position + displacement)
                    max_displacement = max(max_displacement, displacement.magnitude())

            temperature *= self.config.cooling_factor
            if temperature < self.config.min_temperature:
                break
            if max_displacement < self.config.convergence_threshold:
                break

        # Re-center the whole topology on the bounds' center (FR-008). Per-node
        # clamping above only guarantees each node stays inside the bounds — it
        # says nothing about where the topology AS A WHOLE converges, which can
        # drift toward one corner. This is the exact centering fix carried over
        # from ue5-network-viz/layout.py (originally fixed there 2026-07-02/03).
        centroid = Vector3(
            sum(n.position.x for n in node_list) / len(node_list),
            sum(n.position.y for n in node_list) / len(node_list),
            sum(n.position.z for n in node_list) / len(node_list),
        )
        target_center = Vector3(
            (self.config.bounds_min.x + self.config.bounds_max.x) / 2,
            (self.config.bounds_min.y + self.config.bounds_max.y) / 2,
            (self.config.bounds_min.z + self.config.bounds_max.z) / 2,
        )
        offset = target_center - centroid
        for node in node_list:
            node.position = self._apply_bounds(node.position + offset)

        return {node.id: node.position for node in node_list}


def calculate_topology_layout(
    devices: list[Device], links: list[Link], config: Optional[LayoutConfig] = None
) -> dict[str, Vector3]:
    """Assign a centered, scaled Vector3 position to every device in-place and return the mapping."""
    layout = ForceDirectedLayout(config)

    for device in devices:
        layout.add_node(node_id=device.hostname, device_role=device.role.value)

    for link in links:
        layout.add_edge(source_id=link.endpoint_a.hostname, target_id=link.endpoint_b.hostname)

    positions = layout.run()
    for device in devices:
        if device.hostname in positions:
            device.position = positions[device.hostname]
    return positions
