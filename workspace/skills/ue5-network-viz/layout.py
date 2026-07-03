"""
Force-Directed Layout Algorithm for Network Topology Visualization.

This module implements a spring-based force-directed layout algorithm
for positioning network devices in 3D space. The algorithm simulates
physical forces between nodes to produce aesthetically pleasing,
collision-free layouts.

Based on Fruchterman-Reingold with 3D extension and network-specific
optimizations (device type clustering, link-based attraction).
"""

import math
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Vector3:
    """3D coordinate or force vector."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vector3":
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __truediv__(self, scalar: float) -> "Vector3":
        if scalar == 0:
            return Vector3(0, 0, 0)
        return Vector3(self.x / scalar, self.y / scalar, self.z / scalar)

    def magnitude(self) -> float:
        """Calculate vector length."""
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def normalized(self) -> "Vector3":
        """Return unit vector in same direction."""
        mag = self.magnitude()
        if mag == 0:
            return Vector3(0, 0, 0)
        return self / mag

    def to_list(self) -> list[float]:
        """Convert to [x, y, z] list for UE5 MCP."""
        return [self.x, self.y, self.z]

    @classmethod
    def random(cls, min_val: float = -100, max_val: float = 100) -> "Vector3":
        """Create a random vector within bounds."""
        return cls(
            random.uniform(min_val, max_val),
            random.uniform(min_val, max_val),
            random.uniform(min_val, max_val),
        )


@dataclass
class LayoutNode:
    """A node in the force-directed layout graph."""
    id: str
    device_type: str = "unknown"
    position: Vector3 = field(default_factory=Vector3)
    velocity: Vector3 = field(default_factory=Vector3)
    fixed: bool = False  # If True, position won't change


@dataclass
class LayoutEdge:
    """An edge (link) in the layout graph."""
    source_id: str
    target_id: str
    weight: float = 1.0  # Higher weight = stronger attraction


@dataclass
class LayoutConfig:
    """Configuration for the force-directed layout algorithm."""
    # Force parameters
    repulsion_strength: float = 5000.0  # Coulomb's law constant
    attraction_strength: float = 0.1   # Spring constant
    ideal_edge_length: float = 300.0   # Target distance between connected nodes

    # Type clustering - nodes of same type attract slightly
    type_clustering_strength: float = 0.02

    # Simulation parameters
    max_iterations: int = 100
    cooling_factor: float = 0.95      # Temperature decay per iteration
    initial_temperature: float = 100.0
    min_temperature: float = 0.1
    convergence_threshold: float = 0.5  # Stop if max displacement < this

    # Bounds (UE5 coordinates in centimeters)
    bounds_min: Vector3 = field(default_factory=lambda: Vector3(-2000, -2000, 0))
    bounds_max: Vector3 = field(default_factory=lambda: Vector3(2000, 2000, 1000))

    # Scale factor (convert to UE5 centimeters)
    scale: float = 100.0


class ForceDirectedLayout:
    """
    Force-directed layout algorithm for network topology.

    Uses Fruchterman-Reingold algorithm extended to 3D with:
    - Repulsive forces between all nodes (Coulomb's law)
    - Attractive forces along edges (Hooke's law)
    - Optional type-based clustering
    - Simulated annealing for convergence
    """

    def __init__(self, config: Optional[LayoutConfig] = None):
        """Initialize layout algorithm with configuration."""
        self.config = config or LayoutConfig()
        self.nodes: dict[str, LayoutNode] = {}
        self.edges: list[LayoutEdge] = []

    def add_node(
        self,
        node_id: str,
        device_type: str = "unknown",
        position: Optional[Vector3] = None,
        fixed: bool = False,
    ) -> LayoutNode:
        """
        Add a node to the layout.

        Args:
            node_id: Unique identifier (hostname)
            device_type: Device type for clustering
            position: Initial position (random if None)
            fixed: If True, position won't be modified

        Returns:
            The created LayoutNode
        """
        if position is None:
            # Random initial position within bounds
            position = Vector3(
                random.uniform(self.config.bounds_min.x, self.config.bounds_max.x),
                random.uniform(self.config.bounds_min.y, self.config.bounds_max.y),
                random.uniform(self.config.bounds_min.z, self.config.bounds_max.z),
            )

        node = LayoutNode(
            id=node_id,
            device_type=device_type,
            position=position,
            fixed=fixed,
        )
        self.nodes[node_id] = node
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        weight: float = 1.0,
    ) -> Optional[LayoutEdge]:
        """
        Add an edge (link) between two nodes.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            weight: Edge weight (higher = stronger attraction)

        Returns:
            The created LayoutEdge, or None if nodes don't exist
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            return None

        edge = LayoutEdge(source_id, target_id, weight)
        self.edges.append(edge)
        return edge

    def _calculate_repulsion(self, node1: LayoutNode, node2: LayoutNode) -> Vector3:
        """Calculate repulsive force between two nodes (Coulomb's law)."""
        delta = node1.position - node2.position
        distance = delta.magnitude()

        if distance < 1:  # Prevent division by zero
            distance = 1

        # F = k / d^2 (inverse square law)
        force_magnitude = self.config.repulsion_strength / (distance * distance)
        return delta.normalized() * force_magnitude

    def _calculate_attraction(self, edge: LayoutEdge) -> tuple[Vector3, Vector3]:
        """
        Calculate attractive force along an edge (Hooke's law).

        Returns:
            Tuple of (force on source, force on target)
        """
        source = self.nodes[edge.source_id]
        target = self.nodes[edge.target_id]

        delta = target.position - source.position
        distance = delta.magnitude()

        if distance < 1:
            distance = 1

        # F = k * (d - ideal) (spring force)
        displacement = distance - self.config.ideal_edge_length
        force_magnitude = self.config.attraction_strength * displacement * edge.weight

        direction = delta.normalized()
        force_to_target = direction * (-force_magnitude)
        force_to_source = direction * force_magnitude

        return force_to_source, force_to_target

    def _calculate_type_clustering(self, node1: LayoutNode, node2: LayoutNode) -> Vector3:
        """Calculate clustering force between same-type nodes."""
        if node1.device_type != node2.device_type:
            return Vector3(0, 0, 0)

        delta = node2.position - node1.position
        distance = delta.magnitude()

        if distance < 1:
            return Vector3(0, 0, 0)

        # Slight attraction between same-type nodes
        force_magnitude = self.config.type_clustering_strength * distance
        return delta.normalized() * force_magnitude

    def _apply_bounds(self, position: Vector3) -> Vector3:
        """Constrain position to layout bounds."""
        return Vector3(
            max(self.config.bounds_min.x, min(self.config.bounds_max.x, position.x)),
            max(self.config.bounds_min.y, min(self.config.bounds_max.y, position.y)),
            max(self.config.bounds_min.z, min(self.config.bounds_max.z, position.z)),
        )

    def run(self) -> dict[str, Vector3]:
        """
        Run the force-directed layout algorithm.

        Returns:
            Dictionary mapping node IDs to their final positions
        """
        if len(self.nodes) == 0:
            return {}

        if len(self.nodes) == 1:
            # Single node - center it
            node = list(self.nodes.values())[0]
            center = Vector3(
                (self.config.bounds_min.x + self.config.bounds_max.x) / 2,
                (self.config.bounds_min.y + self.config.bounds_max.y) / 2,
                (self.config.bounds_min.z + self.config.bounds_max.z) / 2,
            )
            node.position = center
            return {node.id: node.position}

        temperature = self.config.initial_temperature
        node_list = list(self.nodes.values())

        for iteration in range(self.config.max_iterations):
            # Calculate forces on each node
            forces: dict[str, Vector3] = {n.id: Vector3() for n in node_list}

            # Repulsive forces between all pairs
            for i, node1 in enumerate(node_list):
                for node2 in node_list[i + 1:]:
                    repulsion = self._calculate_repulsion(node1, node2)
                    forces[node1.id] = forces[node1.id] + repulsion
                    forces[node2.id] = forces[node2.id] - repulsion

                    # Type clustering
                    clustering = self._calculate_type_clustering(node1, node2)
                    forces[node1.id] = forces[node1.id] + clustering
                    forces[node2.id] = forces[node2.id] - clustering

            # Attractive forces along edges
            for edge in self.edges:
                force_source, force_target = self._calculate_attraction(edge)
                forces[edge.source_id] = forces[edge.source_id] + force_source
                forces[edge.target_id] = forces[edge.target_id] + force_target

            # Apply forces with temperature limiting
            max_displacement = 0.0
            for node in node_list:
                if node.fixed:
                    continue

                force = forces[node.id]
                force_mag = force.magnitude()

                if force_mag > 0:
                    # Limit displacement by temperature
                    displacement = force.normalized() * min(force_mag, temperature)
                    node.position = node.position + displacement
                    node.position = self._apply_bounds(node.position)

                    max_displacement = max(max_displacement, displacement.magnitude())

            # Cool down
            temperature *= self.config.cooling_factor

            # Check convergence
            if temperature < self.config.min_temperature:
                break
            if max_displacement < self.config.convergence_threshold:
                break

        # Re-center the whole topology on the map's origin.
        #
        # _apply_bounds() above only guarantees each INDIVIDUAL node stays
        # within [bounds_min, bounds_max] — it says nothing about where the
        # topology as a WHOLE ends up. The repulsion/attraction simulation
        # can easily converge with the entire cluster drifted toward one
        # corner or edge of the bounds (observed live 2026-07-02: a rebuilt
        # topology landed off the main map). Fix that by translating every
        # node by the same rigid offset so the topology's own centroid sits
        # at the bounds' center, then re-clamp in case that shift pushed an
        # outlier node past the edge.
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

        # Return final positions
        return {node.id: node.position for node in node_list}

    def get_positions(self) -> dict[str, list[float]]:
        """
        Get node positions as lists for UE5 MCP.

        Returns:
            Dictionary mapping node IDs to [x, y, z] lists
        """
        return {node_id: pos.to_list() for node_id, pos in self.run().items()}


def calculate_topology_layout(
    devices: list[dict],
    links: list[dict],
    config: Optional[LayoutConfig] = None,
) -> dict[str, list[float]]:
    """
    Calculate 3D positions for a network topology.

    Args:
        devices: List of device dicts with 'hostname' and 'device_type'
        links: List of link dicts with 'source_device' and 'target_device'
        config: Optional layout configuration

    Returns:
        Dictionary mapping hostnames to [x, y, z] positions
    """
    layout = ForceDirectedLayout(config)

    # Add nodes
    for device in devices:
        layout.add_node(
            node_id=device.get("hostname", ""),
            device_type=device.get("device_type", "unknown"),
        )

    # Add edges
    for link in links:
        layout.add_edge(
            source_id=link.get("source_device", ""),
            target_id=link.get("target_device", ""),
        )

    return layout.get_positions()
