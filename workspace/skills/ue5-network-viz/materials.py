"""
Material Definitions for UE5 Network Visualization.

This module defines color mappings and material configurations for
network device types and health states. Materials are created as
dynamic material instances in UE5 for real-time color updates.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass
class Color:
    """
    Linear RGB color (0.0-1.0 range) for UE5 materials.

    UE5 uses linear color space, not sRGB.
    """
    r: float
    g: float
    b: float
    a: float = 1.0

    def to_list(self) -> list[float]:
        """Convert to [r, g, b] list for MCP."""
        return [self.r, self.g, self.b]

    def to_rgba_list(self) -> list[float]:
        """Convert to [r, g, b, a] list."""
        return [self.r, self.g, self.b, self.a]

    @classmethod
    def from_hex(cls, hex_color: str) -> "Color":
        """Create Color from hex string (e.g., '#3366CC')."""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return cls(r, g, b)


class DeviceType(Enum):
    """Network device types with associated visual properties."""
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    ENDPOINT = "endpoint"
    ACCESS_POINT = "access_point"
    LOAD_BALANCER = "load_balancer"
    UNKNOWN = "unknown"


class DeviceStatus(Enum):
    """Device operational status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


class LinkStatus(Enum):
    """Link operational status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


# =============================================================================
# Device Type Color Mappings
# =============================================================================

DEVICE_TYPE_COLORS: dict[DeviceType, Color] = {
    DeviceType.ROUTER: Color(0.2, 0.4, 0.8),        # Blue #3366CC
    DeviceType.SWITCH: Color(0.2, 0.7, 0.3),        # Green #33B34D
    DeviceType.FIREWALL: Color(0.8, 0.2, 0.2),      # Red #CC3333
    DeviceType.ACCESS_POINT: Color(0.9, 0.8, 0.2),  # Yellow #E6CC33
    DeviceType.LOAD_BALANCER: Color(0.6, 0.2, 0.8), # Purple #9933CC
    DeviceType.ENDPOINT: Color(0.5, 0.5, 0.5),      # Gray #808080
    DeviceType.UNKNOWN: Color(1.0, 1.0, 1.0),       # White #FFFFFF
}


def get_device_type_color(device_type: str) -> Color:
    """
    Get the color for a device type.

    Args:
        device_type: Device type string (e.g., 'router', 'switch')

    Returns:
        Color for the device type
    """
    try:
        dt = DeviceType(device_type.lower())
    except ValueError:
        dt = DeviceType.UNKNOWN
    return DEVICE_TYPE_COLORS[dt]


# =============================================================================
# Device Status Color Mappings (Override device type color)
# =============================================================================

DEVICE_STATUS_COLORS: dict[DeviceStatus, Color] = {
    DeviceStatus.HEALTHY: Color(0, 0, 0),           # No override (use device type)
    DeviceStatus.WARNING: Color(1.0, 0.6, 0.0),     # Orange
    DeviceStatus.CRITICAL: Color(1.0, 0.0, 0.0),    # Bright Red
    DeviceStatus.UNREACHABLE: Color(0.5, 0.0, 0.0), # Dark Red
    DeviceStatus.UNKNOWN: Color(0.5, 0.5, 0.5),     # Gray
}


def get_device_status_color(status: str) -> Optional[Color]:
    """
    Get the override color for a device status.

    Args:
        status: Device status string

    Returns:
        Color to override base color, or None if no override needed (healthy)
    """
    try:
        ds = DeviceStatus(status.lower())
    except ValueError:
        ds = DeviceStatus.UNKNOWN

    if ds == DeviceStatus.HEALTHY:
        return None  # No override
    return DEVICE_STATUS_COLORS[ds]


# =============================================================================
# Link Status Color Mappings
# =============================================================================

LINK_STATUS_COLORS: dict[LinkStatus, Color] = {
    LinkStatus.HEALTHY: Color(0.2, 0.8, 0.2),   # Green
    LinkStatus.DEGRADED: Color(1.0, 0.8, 0.0),  # Yellow
    LinkStatus.DOWN: Color(0.8, 0.2, 0.2),      # Red
    LinkStatus.UNKNOWN: Color(0.5, 0.5, 0.5),   # Gray
}


def get_link_status_color(status: str) -> Color:
    """
    Get the color for a link status.

    Args:
        status: Link status string

    Returns:
        Color for the link
    """
    try:
        ls = LinkStatus(status.lower())
    except ValueError:
        ls = LinkStatus.UNKNOWN
    return LINK_STATUS_COLORS[ls]


# =============================================================================
# Material Configuration
# =============================================================================

@dataclass
class MaterialConfig:
    """Configuration for a UE5 material instance."""
    name: str
    base_color: Color
    metallic: float = 0.0
    roughness: float = 0.7
    emissive_color: Optional[Color] = None
    emissive_intensity: float = 0.0

    def to_mcp_params(self) -> list[dict]:
        """
        Convert to list of MCP set_material_parameter calls.

        Returns:
            List of dicts with parameter name and value
        """
        params = [
            {"parameter": "BaseColor", "value": self.base_color.to_list()},
            {"parameter": "Metallic", "value": self.metallic},
            {"parameter": "Roughness", "value": self.roughness},
        ]

        if self.emissive_color and self.emissive_intensity > 0:
            params.extend([
                {"parameter": "EmissiveColor", "value": self.emissive_color.to_list()},
                {"parameter": "EmissiveIntensity", "value": self.emissive_intensity},
            ])

        return params


def create_device_material_config(
    device_type: str,
    status: str = "healthy",
    hostname: str = "",
) -> MaterialConfig:
    """
    Create material configuration for a network device.

    Args:
        device_type: Device type string
        status: Device status string
        hostname: Device hostname (used in material name)

    Returns:
        MaterialConfig ready for UE5 material creation
    """
    # Base color from device type
    base_color = get_device_type_color(device_type)

    # Status override
    status_color = get_device_status_color(status)
    if status_color:
        base_color = status_color

    # Generate material name
    safe_hostname = hostname.replace("-", "_").replace(".", "_")
    material_name = f"MI_Device_{safe_hostname}" if hostname else f"MI_{device_type}"

    # Configure emissive for critical/warning states
    emissive_color = None
    emissive_intensity = 0.0

    try:
        ds = DeviceStatus(status.lower())
        if ds == DeviceStatus.CRITICAL:
            emissive_color = Color(1.0, 0.0, 0.0)  # Red glow
            emissive_intensity = 5.0
        elif ds == DeviceStatus.WARNING:
            emissive_color = Color(1.0, 0.6, 0.0)  # Orange glow
            emissive_intensity = 2.0
        elif ds == DeviceStatus.UNREACHABLE:
            emissive_color = Color(0.5, 0.0, 0.0)  # Dark red glow
            emissive_intensity = 3.0
    except ValueError:
        pass

    return MaterialConfig(
        name=material_name,
        base_color=base_color,
        metallic=0.2,
        roughness=0.6,
        emissive_color=emissive_color,
        emissive_intensity=emissive_intensity,
    )


def create_link_material_config(
    status: str = "healthy",
    link_id: str = "",
) -> MaterialConfig:
    """
    Create material configuration for a network link.

    Args:
        status: Link status string
        link_id: Link identifier (used in material name)

    Returns:
        MaterialConfig ready for UE5 material creation
    """
    base_color = get_link_status_color(status)

    # Generate material name
    safe_link_id = link_id.replace("-", "_").replace(".", "_")
    material_name = f"MI_Link_{safe_link_id}" if link_id else f"MI_Link_{status}"

    # Emissive for problem states
    emissive_color = None
    emissive_intensity = 0.0

    try:
        ls = LinkStatus(status.lower())
        if ls == LinkStatus.DOWN:
            emissive_color = Color(0.8, 0.0, 0.0)
            emissive_intensity = 3.0
        elif ls == LinkStatus.DEGRADED:
            emissive_color = Color(1.0, 0.8, 0.0)
            emissive_intensity = 1.5
    except ValueError:
        pass

    return MaterialConfig(
        name=material_name,
        base_color=base_color,
        metallic=0.0,
        roughness=0.8,
        emissive_color=emissive_color,
        emissive_intensity=emissive_intensity,
    )


# =============================================================================
# Device Type Inference
# =============================================================================

DEVICE_TYPE_PATTERNS: dict[DeviceType, list[str]] = {
    DeviceType.ROUTER: [
        "rtr", "router", "cr", "er", "br", "core", "edge", "border",
        "isr", "asr", "csr", "nexus", "nxos",
    ],
    DeviceType.SWITCH: [
        "sw", "switch", "ds", "as", "access", "distribution", "tor",
        "leaf", "spine", "catalyst", "n3k", "n5k", "n7k", "n9k",
    ],
    DeviceType.FIREWALL: [
        "fw", "firewall", "asa", "ftd", "palo", "fortigate", "checkpoint",
        "srx", "pfsense", "pan", "fmc",
    ],
    DeviceType.ACCESS_POINT: [
        "ap", "wap", "wireless", "wlc", "wifi", "aruba", "meraki-ap",
        "air", "aironet",
    ],
    DeviceType.LOAD_BALANCER: [
        "lb", "f5", "bigip", "netscaler", "haproxy", "alb", "elb", "nlb",
        "avi", "citrix", "a10",
    ],
    DeviceType.ENDPOINT: [
        "pc", "host", "server", "vm", "workstation", "laptop", "desktop",
        "srv", "node", "instance",
    ],
}


def infer_device_type(hostname: str, model: str = "") -> str:
    """
    Infer device type from hostname and optional model string.

    Args:
        hostname: Device hostname
        model: Optional device model string

    Returns:
        Device type string (e.g., 'router', 'switch')
    """
    search_text = f"{hostname} {model}".lower()

    for device_type, patterns in DEVICE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in search_text:
                return device_type.value

    return DeviceType.UNKNOWN.value
