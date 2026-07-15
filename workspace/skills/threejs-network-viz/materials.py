"""
Role- and state-based color tables plus hostname-based device-role inference
for the Three.js network topology visualization skill.

Role-color table and infer_device_role() are ported/adapted from
workspace/skills/ue5-network-viz/materials.py's DEVICE_TYPE_COLORS /
infer_device_type (research.md §4). State-color table is this skill's own
addition (User Story 4, FR-016/FR-017) — spec.md's minimum role set has no
separate "access point" role, so the UE5 port's access-point hostname
patterns are folded into the SWITCH bucket here (an AP behaves as an L2
attachment point in a topology diagram, same as a switch).
"""

import re

from topology_model import DeviceRole, OperationalState

# =============================================================================
# Role colors (FR-002) — used for the default procedural shape/legend
# =============================================================================

DEVICE_ROLE_COLORS: dict[DeviceRole, str] = {
    DeviceRole.ROUTER: "#3366CC",  # Blue
    DeviceRole.SWITCH: "#33B34D",  # Green
    DeviceRole.FIREWALL: "#CC3333",  # Red
    DeviceRole.LOAD_BALANCER: "#9933CC",  # Purple
    DeviceRole.CLIENT: "#E68019",  # Orange
    DeviceRole.UNCLASSIFIED: "#FFFFFF",  # White
}

DEVICE_ROLE_SHAPES: dict[DeviceRole, str] = {
    DeviceRole.ROUTER: "box",
    DeviceRole.SWITCH: "box",
    DeviceRole.FIREWALL: "cylinder",
    DeviceRole.LOAD_BALANCER: "cylinder",
    DeviceRole.CLIENT: "extruded_icon",
    DeviceRole.UNCLASSIFIED: "extruded_icon",
}


def get_device_role_color(role: DeviceRole) -> str:
    return DEVICE_ROLE_COLORS[role]


def get_device_role_shape(role: DeviceRole) -> str:
    return DEVICE_ROLE_SHAPES[role]


def generate_role_legend_entries() -> list[dict]:
    """Legend entries generated live from DEVICE_ROLE_COLORS so the legend can
    never drift out of sync with the colors actually used (mirrors the same
    freshness guarantee already established in ue5-network-viz/materials.py)."""
    return [
        {
            "role": role.value,
            "label": role.value.replace("_", " ").title(),
            "color": DEVICE_ROLE_COLORS[role],
            "shape": DEVICE_ROLE_SHAPES[role],
        }
        for role in DeviceRole
    ]


# =============================================================================
# State colors (User Story 4, FR-016/FR-017) — overlay on top of role color
# =============================================================================

STATE_COLORS: dict[OperationalState, str] = {
    # Deliberately chosen from hues that do NOT appear anywhere in
    # DEVICE_ROLE_COLORS above (blue/green/red/purple/orange/white) — a
    # naive first pass reused green for HEALTHY and red for DOWN, which
    # collided with SWITCH and FIREWALL's role colors respectively (a
    # healthy switch and a down firewall would have rendered identically to
    # their own always-on role color, silently defeating FR-016's "state
    # must be visually distinguishable" requirement). Found via
    # test_threejs_scene_builder.py's state-vs-role-color regression test.
    OperationalState.HEALTHY: "#00E5FF",  # Cyan
    OperationalState.DEGRADED: "#FFD500",  # Gold
    OperationalState.DOWN: "#1A1A1A",  # Near-black
    OperationalState.UNKNOWN: "#808080",  # Neutral gray — never implies a state
}


def get_state_color(state) -> str | None:
    """Return the state overlay color, or None when state is absent (renders
    the neutral role-based default per FR-017) — distinct from UNKNOWN, which
    is an explicit "source reported no data" signal that still renders neutral."""
    if state is None:
        return None
    return STATE_COLORS[state]


def generate_state_legend_entries() -> list[dict]:
    return [
        {"state": state.value, "label": state.value.title(), "color": color}
        for state, color in STATE_COLORS.items()
    ]


# =============================================================================
# Device role inference from hostname/model (ported from ue5-network-viz)
# =============================================================================

DEVICE_ROLE_PATTERNS: dict[DeviceRole, list[str]] = {
    DeviceRole.ROUTER: [
        "rtr", "router", "cr", "er", "br", "core", "edge", "border",
        "isr", "asr", "csr", "nexus", "nxos",
    ],
    DeviceRole.SWITCH: [
        "sw", "switch", "ds", "as", "access", "distribution", "tor",
        "leaf", "spine", "catalyst", "n3k", "n5k", "n7k", "n9k",
        # Access-point patterns folded in here — spec.md's minimum role set
        # has no standalone "access point" role (see module docstring).
        "ap", "wap", "wireless", "wlc", "wifi", "aruba", "meraki-ap",
        "air", "aironet",
    ],
    DeviceRole.FIREWALL: [
        "fw", "firewall", "asa", "ftd", "palo", "fortigate", "checkpoint",
        "srx", "pfsense", "pan", "fmc",
    ],
    DeviceRole.LOAD_BALANCER: [
        "lb", "f5", "bigip", "netscaler", "haproxy", "alb", "elb", "nlb",
        "avi", "citrix", "a10",
    ],
    DeviceRole.CLIENT: [
        "pc", "host", "server", "vm", "workstation", "laptop", "desktop",
        "srv", "node", "instance", "client",
    ],
}


def infer_device_role(hostname: str, model: str = "") -> DeviceRole:
    """Infer a DeviceRole from hostname/model text; UNCLASSIFIED is the
    explicit, always-rendered fallback (Edge Cases in spec.md), never omitted.

    Matches against whole alphanumeric TOKENS (split on any non-alphanumeric
    character), not a raw substring search across the full string — a naive
    substring search on a short pattern like "er" (meant for names like
    "er1"/"edge-router") false-positives inside unrelated words such as
    "mystery-box" (contains "er"). A token counts as a match if it equals a
    pattern exactly or starts with it (so "rtr1", "sw12", "isr4321" still
    match "rtr"/"sw"/"isr" as a prefix of a compound token)."""
    search_text = f"{hostname} {model}".lower()
    tokens = re.findall(r"[a-z0-9]+", search_text)
    for role, patterns in DEVICE_ROLE_PATTERNS.items():
        for pattern in patterns:
            if any(token == pattern or token.startswith(pattern) for token in tokens):
                return role
    return DeviceRole.UNCLASSIFIED
