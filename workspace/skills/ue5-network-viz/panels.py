"""
Panels for UE5 Network Digital Twin (045-ue5-digital-twin).

Shared `_render_panel()` primitive backs both US8 (on-demand config panels)
and US12 (the floating metrics HUD): a repeat request for the same
(hostname, panel_kind) replaces the existing panel actor instead of
stacking a duplicate (FR-025/FR-037).
"""

import json

try:
    from .ue5_mcp_client import UE5MCPClient
    from .actors import PROGRAMMATIC_TOOLSET, TOOL_EXECUTE_SCRIPT, NETCLAW_TAG, is_device_in_topology
    from .scene import get_device_position
except ImportError:  # pragma: no cover - fallback for sys.path-style loading
    from ue5_mcp_client import UE5MCPClient
    from actors import PROGRAMMATIC_TOOLSET, TOOL_EXECUTE_SCRIPT, NETCLAW_TAG, is_device_in_topology
    from scene import get_device_position

# Stacked vertically above the device so config + metrics panels for the
# same device never overlap.
_PANEL_HEIGHT_OFFSETS = {"config": 220.0, "metrics": 420.0}


def generate_panel_actor_name(hostname: str, panel_kind: str) -> str:
    """Generate UE5 actor name for a device's panel (FR-025/FR-037)."""
    safe = hostname.replace("-", "_").replace(".", "_").replace(" ", "_")
    return f"NC_Panel_{panel_kind}_{safe}"


async def _render_panel(client: UE5MCPClient, hostname: str, panel_kind: str, content: str) -> bool:
    """
    Spawn (or replace) a readable text panel near a device's actor. Destroys
    any existing actor with this exact (hostname, panel_kind) label first,
    then spawns a fresh one with the new content — so a repeated request
    replaces rather than duplicates (FR-025/FR-037).
    """
    position = get_device_position(hostname)
    if position is None:
        return False

    actor_name = generate_panel_actor_name(hostname, panel_kind)
    height = _PANEL_HEIGHT_OFFSETS.get(panel_kind, 620.0)
    location = [position[0], position[1], position[2] + height]

    payload = {"actor_name": actor_name, "location": location, "text": content, "panel_kind": panel_kind}
    script = f'''
import json
import unreal

_data = json.loads({json.dumps(json.dumps(payload))})
_editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
_ok = False
try:
    for a in list(_editor.get_all_level_actors()):
        if a.get_actor_label() == _data["actor_name"]:
            _editor.destroy_actor(a)

    loc = _data["location"]
    text_actor = _editor.spawn_actor_from_class(
        unreal.TextRenderActor, unreal.Vector(loc[0], loc[1], loc[2]), unreal.Rotator(0, 0, 0)
    )
    if text_actor:
        text_component = text_actor.get_component_by_class(unreal.TextRenderComponent)
        if text_component:
            text_component.set_text(_data["text"])
            text_component.set_world_size(35.0)
            text_component.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_LEFT)
        text_actor.set_actor_label(_data["actor_name"])
        text_actor.tags.append("{NETCLAW_TAG}")
        text_actor.tags.append("panel")
        text_actor.tags.append(_data["panel_kind"])
        for comp in text_actor.get_components_by_class(unreal.BillboardComponent):
            comp.set_visibility(False)
            comp.set_hidden_in_game(True)
        _ok = True
except Exception as exc:
    unreal.log_error("_render_panel failed: " + str(exc))
    _ok = False

result = json.dumps({{"rendered": _ok}})
print(result)
'''
    exec_result = await client.call_tool(
        toolset_name=PROGRAMMATIC_TOOLSET,
        tool_name=TOOL_EXECUTE_SCRIPT,
        arguments={"script": script},
    )
    if not exec_result.success:
        return False
    if isinstance(exec_result.data, dict):
        return bool(exec_result.data.get("rendered", False))
    return True


async def show_config_panel(client: UE5MCPClient, hostname: str, running_config: str) -> dict:
    """
    US8 (FR-024/FR-025): render a device's real running-config (already
    retrieved by the calling agent via gnmi-mcp/pyATS) as a readable panel
    near its actor. Refuses rather than attempts for a device not in the
    current topology (FR-040).
    """
    if not is_device_in_topology(hostname):
        return {"rendered": False, "reason": f"{hostname} not in current topology"}

    ok = await _render_panel(client, hostname, "config", running_config)
    return {"rendered": ok, "hostname": hostname, "panel_kind": "config"}


async def show_metrics_hud(
    client: UE5MCPClient,
    hostname: str,
    cpu_percent: float,
    memory_percent: float,
    uptime: str,
) -> dict:
    """
    US12 (FR-036/FR-037): render a device's live CPU/memory/uptime (already
    retrieved by the calling agent via gnmi-mcp/pyATS) as a floating panel
    above its actor. Reuses the same `_render_panel` destroy-then-recreate
    primitive as `show_config_panel`, so a repeated request always shows the
    freshly-supplied values passed in this call — nothing is cached from a
    prior request (FR-037). Refuses rather than attempts for a device not in
    the current topology (FR-040).
    """
    if not is_device_in_topology(hostname):
        return {"rendered": False, "reason": f"{hostname} not in current topology"}

    content = f"METRICS: {hostname}\nCPU: {cpu_percent:.1f}%\nMemory: {memory_percent:.1f}%\nUptime: {uptime}"
    ok = await _render_panel(client, hostname, "metrics", content)
    return {"rendered": ok, "hostname": hostname, "panel_kind": "metrics"}
