"""
Hierarchical Zoom for UE5 Network Digital Twin (045-ue5-digital-twin, US11).

Groups devices into site/rack/device-level zoom groups, sourced from
NetBox/Infrahub first with a manual fallback (FR-033, per the clarify-phase
decision to prefer real source-of-truth placement over manual grouping).
Like the rest of this feature, this module never calls netbox-mcp-server or
infrahub-mcp itself — the calling agent retrieves placement data via those
MCP tools and hands it here as a plain mapping.

zoom_to()/zoom_out_to_site() only toggle actor visibility — they never
destroy or respawn actors, so a zoom transition can't lose or duplicate
anything already in the scene (FR-034/FR-035).
"""

import json
from dataclasses import dataclass, field

try:
    from .ue5_mcp_client import UE5MCPClient
    from .actors import PROGRAMMATIC_TOOLSET, TOOL_EXECUTE_SCRIPT
    from .camera import set_camera_location, set_overview_camera
    from .scene import get_device_position
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from ue5_mcp_client import UE5MCPClient
    from actors import PROGRAMMATIC_TOOLSET, TOOL_EXECUTE_SCRIPT
    from camera import set_camera_location, set_overview_camera
    from scene import get_device_position


@dataclass
class ZoomGroup:
    """One rack/site grouping (data-model.md)."""
    group_name: str
    zoom_level: str  # "site" | "rack" | "device"
    member_hostnames: list[str] = field(default_factory=list)
    source: str = "manual"  # "netbox" | "infrahub" | "manual"


_resolved_groups: dict[str, ZoomGroup] = {}
_hostname_to_group: dict[str, str] = {}


async def resolve_zoom_groups(
    hostnames: list[str],
    placement_by_hostname: dict[str, dict],
) -> list[ZoomGroup]:
    """
    Build zoom groups from real NetBox/Infrahub placement data (FR-033,
    NetBox/Infrahub first per the clarify-phase decision). `placement_by_hostname`
    is `{hostname: {"group_name": str, "zoom_level": str, "source": "netbox"|"infrahub"}}`,
    already retrieved by the calling agent. A hostname with no entry here is
    left ungrouped rather than guessed into an arbitrary group (spec.md edge
    case) — call `assign_manual_group()` for it explicitly if desired.
    """
    groups: dict[str, ZoomGroup] = {}

    for hostname in hostnames:
        placement = placement_by_hostname.get(hostname)
        if not placement:
            continue
        group_name = placement["group_name"]
        if group_name not in groups:
            groups[group_name] = ZoomGroup(
                group_name=group_name,
                zoom_level=placement.get("zoom_level", "rack"),
                source=placement.get("source", "netbox"),
            )
        groups[group_name].member_hostnames.append(hostname)
        _hostname_to_group[hostname] = group_name

    for group in groups.values():
        _resolved_groups[group.group_name] = group

    return list(groups.values())


def assign_manual_group(group_name: str, hostnames: list[str], zoom_level: str = "rack") -> ZoomGroup:
    """
    Manual fallback (FR-033) for devices with no NetBox/Infrahub placement.
    """
    group = ZoomGroup(group_name=group_name, zoom_level=zoom_level, member_hostnames=list(hostnames), source="manual")
    _resolved_groups[group_name] = group
    for hostname in hostnames:
        _hostname_to_group[hostname] = group_name
    return group


def get_ungrouped_hostnames(all_hostnames: list[str]) -> list[str]:
    """Devices with no NetBox/Infrahub placement and no manual assignment (spec.md edge case)."""
    return [h for h in all_hostnames if h not in _hostname_to_group]


def clear_zoom_groups() -> None:
    """Reset the registry (used by tests and by a fresh topology build)."""
    _resolved_groups.clear()
    _hostname_to_group.clear()


async def zoom_to(client: UE5MCPClient, group_name: str) -> dict:
    """
    Show only the actors belonging to `group_name`'s member devices and hide
    everything else, by toggling visibility only (FR-032/FR-034/FR-035) —
    never destroying or respawning actors, so a zoom transition can't lose
    or duplicate anything already in the scene. Frames the camera on the
    group's device centroid.
    """
    group = _resolved_groups.get(group_name)
    if group is None:
        return {"zoomed": False, "reason": f"no resolved zoom group named {group_name}"}

    positions = [p for h in group.member_hostnames if (p := get_device_position(h))]
    if not positions:
        return {"zoomed": False, "reason": f"no positioned devices in group {group_name}"}

    members_json = json.dumps(group.member_hostnames)
    script = f'''
import json
import unreal

_members = json.loads({json.dumps(members_json)})
_editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
_shown = 0
_hidden = 0
try:
    for a in _editor.get_all_level_actors():
        label = a.get_actor_label()
        if not label.startswith("NC_"):
            continue
        # Actor labels embed the owning hostname (device: NC_<host>,
        # interface: NC_If_<host>_<iface>, link: NC_Link_<host10>_<host10> —
        # link names truncate each hostname to 10 chars, a pre-existing
        # limitation, so very long hostnames may not match on link actors).
        belongs = any(m in label for m in _members)
        a.set_is_temporarily_hidden_in_editor(not belongs)
        a.set_actor_hidden_in_game(not belongs)
        if belongs:
            _shown += 1
        else:
            _hidden += 1
except Exception as exc:
    unreal.log_error("zoom_to failed: " + str(exc))

result = json.dumps({{"shown": _shown, "hidden": _hidden}})
print(result)
'''
    exec_result = await client.call_tool(
        toolset_name=PROGRAMMATIC_TOOLSET,
        tool_name=TOOL_EXECUTE_SCRIPT,
        arguments={"script": script},
    )

    center = [sum(p[i] for p in positions) / len(positions) for i in range(3)]
    await set_camera_location(client, [center[0] - 400, center[1] - 400, center[2] + 300], [-30, 45, 0])

    return {"zoomed": exec_result.success, "group_name": group_name, "member_count": len(group.member_hostnames)}


async def zoom_out_to_site(client: UE5MCPClient) -> dict:
    """Restore visibility of every NetClaw actor (undo any zoom_to filtering) and reframe the overview camera."""
    script = '''
import json
import unreal

_editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
_shown = 0
try:
    for a in _editor.get_all_level_actors():
        if a.get_actor_label().startswith("NC_"):
            a.set_is_temporarily_hidden_in_editor(False)
            a.set_actor_hidden_in_game(False)
            _shown += 1
except Exception as exc:
    unreal.log_error("zoom_out_to_site failed: " + str(exc))

result = json.dumps({"shown": _shown})
print(result)
'''
    exec_result = await client.call_tool(
        toolset_name=PROGRAMMATIC_TOOLSET,
        tool_name=TOOL_EXECUTE_SCRIPT,
        arguments={"script": script},
    )
    await set_overview_camera(client)
    return {"zoomed_out": exec_result.success}
