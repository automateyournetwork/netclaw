"""
Canonical topology data model for the Three.js browser network visualization skill.

Every topology-source adapter in sources.py (live source or freeform) MUST
produce these types, and every downstream module (layout.py, materials.py,
assets.py, scene_builder.py) consumes only these types — never a
source-specific shape. See specs/046-threejs-network-viz/data-model.md.
"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class DeviceRole(str, Enum):
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    LOAD_BALANCER = "load_balancer"
    CLIENT = "client"
    UNCLASSIFIED = "unclassified"


class OperationalState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class SourceKind(str, Enum):
    CML = "cml"
    GNS3 = "gns3"
    CONTAINERLAB = "containerlab"
    EVE_NG = "eve_ng"
    NAUTOBOT = "nautobot"
    NETBOX_INFRAHUB = "netbox_infrahub"
    IP_FABRIC = "ip_fabric"
    FORWARD_NETWORKS = "forward_networks"
    FREEFORM = "freeform"


class AssetKind(str, Enum):
    PROCEDURAL = "procedural"
    REAL_MODEL = "real_model"


class ProceduralShape(str, Enum):
    BOX = "box"
    CYLINDER = "cylinder"
    EXTRUDED_ICON = "extruded_icon"


class ModelSource(str, Enum):
    CACHE = "cache"
    SKETCHFAB = "sketchfab"
    USER_SUPPLIED = "user_supplied"


class FallbackReason(str, Enum):
    NO_CC0_CANDIDATE_FOUND = "no_cc0_candidate_found"
    SOURCE_UNREACHABLE = "source_unreachable"
    GATED_MARKETPLACE_VERIFY_ONLY_NO_ASSET = "gated_marketplace_verify_only_no_asset"


# Forbidden metadata keys — a defensive denylist enforced at assembly time
# (FR-005a). Adapters MUST NOT copy anything matching these into
# Device.metadata / Interface.metadata.
FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "password",
        "secret",
        "credential",
        "credentials",
        "api_key",
        "apikey",
        "token",
        "running_config",
        "startup_config",
        "config",
        "private_key",
    }
)


def sanitize_metadata(raw: Optional[dict]) -> dict:
    """Strip anything resembling a credential/secret/full-config blob (FR-005a)."""
    if not raw:
        return {}
    return {
        str(k): str(v)
        for k, v in raw.items()
        if str(k).strip().lower() not in FORBIDDEN_METADATA_KEYS
    }


@dataclass
class Vector3:
    """3D coordinate or force vector — engine-agnostic scene units."""

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
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalized(self) -> "Vector3":
        mag = self.magnitude()
        if mag == 0:
            return Vector3(0, 0, 0)
        return self / mag

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]

    @classmethod
    def random(cls, min_val: float = -10, max_val: float = 10) -> "Vector3":
        return cls(
            random.uniform(min_val, max_val),
            random.uniform(min_val, max_val),
            random.uniform(min_val, max_val),
        )


@dataclass
class DeviceAsset:
    kind: AssetKind = AssetKind.PROCEDURAL
    procedural_shape: Optional[ProceduralShape] = None
    model_source: Optional[ModelSource] = None
    model_license_slug: Optional[str] = None
    embedded_glb_base64: Optional[str] = None

    def __post_init__(self):
        if self.kind == AssetKind.REAL_MODEL and not self.embedded_glb_base64:
            raise ValueError("A real_model DeviceAsset must carry embedded_glb_base64 (FR-001, FR-019)")
        if self.model_source == ModelSource.SKETCHFAB and self.model_license_slug != "cc0":
            raise ValueError("A sketchfab-sourced DeviceAsset must have model_license_slug == 'cc0' (FR-019a)")


@dataclass
class Interface:
    name: str
    parent_hostname: str
    ip_address: Optional[str] = None
    state: Optional[OperationalState] = None
    metadata: dict = field(default_factory=dict)
    local_offset: Vector3 = field(default_factory=Vector3)


@dataclass
class Device:
    hostname: str
    role: DeviceRole = DeviceRole.UNCLASSIFIED
    state: Optional[OperationalState] = None
    interfaces: list[Interface] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    device_asset: DeviceAsset = field(default_factory=DeviceAsset)
    position: Vector3 = field(default_factory=Vector3)


@dataclass
class LinkEndpoint:
    hostname: str
    interface_name: Optional[str] = None


@dataclass
class Link:
    link_id: str
    endpoint_a: LinkEndpoint
    endpoint_b: LinkEndpoint
    state: Optional[OperationalState] = None
    label: str = ""

    def __post_init__(self):
        if not self.label:
            a = self.endpoint_a
            b = self.endpoint_b
            a_label = f"{a.hostname}:{a.interface_name}" if a.interface_name else a.hostname
            b_label = f"{b.hostname}:{b.interface_name}" if b.interface_name else b.hostname
            self.label = f"{a_label} <-> {b_label}"


@dataclass
class FallbackNote:
    hostname: str
    role: str
    reason: FallbackReason


@dataclass
class TopologySnapshot:
    snapshot_id: str
    source_kind: SourceKind
    source_label: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    devices: list[Device] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    real_stencil_mode: bool = False
    fallback_report: list[FallbackNote] = field(default_factory=list)

    def get_device(self, hostname: str) -> Optional[Device]:
        return next((d for d in self.devices if d.hostname == hostname), None)

    def validate(self) -> None:
        """Enforce data-model.md's validation rules; raises ValueError on violation."""
        hostnames = {d.hostname for d in self.devices}
        for device in self.devices:
            for iface in device.interfaces:
                if iface.parent_hostname != device.hostname:
                    raise ValueError(
                        f"Interface {iface.name!r} parent_hostname {iface.parent_hostname!r} "
                        f"does not match owning Device {device.hostname!r} (FR-003)"
                    )
        for link in self.links:
            for endpoint in (link.endpoint_a, link.endpoint_b):
                if endpoint.hostname not in hostnames:
                    raise ValueError(
                        f"Link {link.link_id!r} references unknown device {endpoint.hostname!r} (FR-004)"
                    )
                if endpoint.interface_name is not None:
                    device = self.get_device(endpoint.hostname)
                    iface_names = {i.name for i in device.interfaces} if device else set()
                    if endpoint.interface_name not in iface_names:
                        raise ValueError(
                            f"Link {link.link_id!r} references unknown interface "
                            f"{endpoint.interface_name!r} on {endpoint.hostname!r} (FR-004)"
                        )
