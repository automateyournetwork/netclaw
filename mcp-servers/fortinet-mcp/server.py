#!/usr/bin/env python3
"""fortinet-mcp — Fortinet coverage across three planes. Spec 080 (roadmap R3).

    manager   FortiManager   intent          — what policy SHOULD be
    device    FortiGate      observed state  — what a box IS doing
    analyzer  FortiAnalyzer  observed traffic— what ACTUALLY hit the policy

Every response carries `plane` and `scope` structurally (FR-005/FR-009) and is
GAIT-audited (FR-023) because it passes through `envelope.emit()`. That is a
chokepoint, not a convention: a new tool cannot forget attribution or auditing.

Read-only by default. The single write tool sits behind two independent gates.

Transport: stdio, FastMCP, JSON-RPC lifecycle (Principle V).
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP  # noqa: E402

import gates  # noqa: E402
from credentials import MissingCredential, load  # noqa: E402
from envelope import Outcome, Plane, emit  # noqa: E402
from planes import analyzer as az  # noqa: E402
from planes import device as dev  # noqa: E402
from planes import manager as mgr  # noqa: E402
from transport.jsonrpc import JsonRpcClient  # noqa: E402
from transport.rest import FortiOSClient  # noqa: E402

mcp = FastMCP("fortinet-mcp")


def _missing(plane: Plane, exc: MissingCredential, tool: str) -> dict[str, Any]:
    """Report an unconfigured plane by variable name, never by value (FR-029)."""
    return emit(plane, source="<unconfigured>", outcome=Outcome.AUTH_MISSING,
                message=str(exc), tool=tool)


def _rest() -> FortiOSClient:
    return FortiOSClient(load(Plane.DEVICE))


def _jsonrpc(plane: Plane) -> JsonRpcClient:
    return JsonRpcClient(load(plane))


# ---------------------------------------------------------------------------
# Device plane — FortiGate (6 tools)
# ---------------------------------------------------------------------------

@mcp.tool()
async def fgt_system_status(vdom: str = "root") -> dict:
    """FortiGate status: hostname, serial, version, HA mode and which member answered."""
    try:
        client = _rest()
    except MissingCredential as exc:
        return _missing(Plane.DEVICE, exc, "fgt_system_status")
    await client.resolve_identity()
    return await dev.system_status(client, vdom)


@mcp.tool()
async def fgt_list_interfaces(vdom: str = "root") -> dict:
    """FortiGate interfaces with link state, addressing and error counters, per VDOM."""
    try:
        client = _rest()
    except MissingCredential as exc:
        return _missing(Plane.DEVICE, exc, "fgt_list_interfaces")
    await client.resolve_identity()
    return await dev.list_interfaces(client, vdom)


@mcp.tool()
async def fgt_get_routes(vdom: str = "root", protocol: str = "") -> dict:
    """FortiGate routing table as observed on the device. Optional protocol filter."""
    try:
        client = _rest()
    except MissingCredential as exc:
        return _missing(Plane.DEVICE, exc, "fgt_get_routes")
    await client.resolve_identity()
    return await dev.get_routes(client, vdom, protocol or None)


@mcp.tool()
async def fgt_vpn_tunnels(vdom: str = "root") -> dict:
    """IPsec tunnel status with phase 1 and phase 2 reported SEPARATELY.

    A tunnel with phase 1 up and phase 2 down is neither up nor down; it is a
    specific fault. Never collapse the two into one status.
    """
    try:
        client = _rest()
    except MissingCredential as exc:
        return _missing(Plane.DEVICE, exc, "fgt_vpn_tunnels")
    await client.resolve_identity()
    return await dev.vpn_tunnels(client, vdom)


@mcp.tool()
async def fgt_get_policies(vdom: str = "root") -> dict:
    """Firewall policy as RUNNING ON THE DEVICE. Compare with the manager for drift."""
    try:
        client = _rest()
    except MissingCredential as exc:
        return _missing(Plane.DEVICE, exc, "fgt_get_policies")
    await client.resolve_identity()
    return await dev.get_policies(client, vdom)


@mcp.tool()
async def fgt_compare_with_manager(adom: str, package: str, vdom: str = "root") -> dict:
    """Report divergence between FortiManager intent and FortiGate running state.

    `only_in_device` is an out-of-band change — the most operationally
    interesting thing this server can surface, and invisible from either plane
    alone. If either plane is unreachable this reports which one, and does NOT
    compare against a plane it could not read (FR-007).
    """
    tool = "fgt_compare_with_manager"
    try:
        rest = _rest()
    except MissingCredential as exc:
        return _missing(Plane.DEVICE, exc, tool)
    try:
        rpc = _jsonrpc(Plane.MANAGER)
    except MissingCredential as exc:
        return _missing(Plane.MANAGER, exc, tool)

    await rest.resolve_identity()
    device_side = await dev.get_policies(rest, vdom)
    manager_side = await mgr.get_policy_package(rpc, adom, package)

    for side, name in ((device_side, "device"), (manager_side, "manager")):
        if side["outcome"] in (Outcome.PLANE_UNREACHABLE.value, Outcome.AUTH_MISSING.value,
                               Outcome.AUTH_EXPIRED.value):
            return emit(
                Plane.DEVICE, source=rest.source,
                scope={"device": rest.device_name, "vdom": vdom},
                outcome=Outcome.PLANE_UNREACHABLE,
                message=f"Cannot compare: the {name} plane did not answer. "
                        f"{side.get('message', '')}",
                notes=["No comparison was performed. Neither plane's data is "
                       "presented as the other's."],
                tool=tool,
            )

    dev_rules = {r["name"] or f"id{r['policyid']}": r for r in device_side["data"]["policies"]}
    mgr_rules = {r["name"] or f"id{r['policyid']}": r for r in manager_side["data"]["rules"]}

    only_device = sorted(set(dev_rules) - set(mgr_rules))
    only_manager = sorted(set(mgr_rules) - set(dev_rules))
    differs = sorted(
        k for k in (set(dev_rules) & set(mgr_rules))
        if dev_rules[k].get("action") != mgr_rules[k].get("action")
        or dev_rules[k].get("status") != mgr_rules[k].get("status")
    )

    notes = []
    if only_device:
        notes.append(
            f"{len(only_device)} rule(s) exist on the device but not in the policy "
            "package — candidate OUT-OF-BAND CHANGES."
        )
    if only_manager:
        notes.append(
            f"{len(only_manager)} rule(s) are in the package but not on the device — "
            "the package may not have been installed since they were added."
        )
    if not (only_device or only_manager or differs):
        notes.append("Intent and observed state agree for all compared rules.")

    return emit(
        Plane.DEVICE, source=rest.source,
        scope={"device": rest.device_name, "vdom": vdom},
        data={
            "planes_consulted": ["manager", "device"],
            "adom": adom, "package": package,
            "only_in_device": only_device,
            "only_in_manager": only_manager,
            "differs": differs,
            "device_rule_count": len(dev_rules),
            "manager_rule_count": len(mgr_rules),
        },
        notes=notes, tool=tool,
    )


# ---------------------------------------------------------------------------
# Manager plane — FortiManager (8 tools)
# ---------------------------------------------------------------------------

@mcp.tool()
async def fmg_list_adoms() -> dict:
    """List FortiManager ADOMs. The ADOM scopes everything else on this plane."""
    try:
        return await mgr.list_adoms(_jsonrpc(Plane.MANAGER))
    except MissingCredential as exc:
        return _missing(Plane.MANAGER, exc, "fmg_list_adoms")


@mcp.tool()
async def fmg_list_devices(adom: str) -> dict:
    """List FortiGates managed within an ADOM, with connection and sync status."""
    try:
        return await mgr.list_devices(_jsonrpc(Plane.MANAGER), adom)
    except MissingCredential as exc:
        return _missing(Plane.MANAGER, exc, "fmg_list_devices")


@mcp.tool()
async def fmg_list_policy_packages(adom: str) -> dict:
    """List policy packages in an ADOM with their install targets."""
    try:
        return await mgr.list_policy_packages(_jsonrpc(Plane.MANAGER), adom)
    except MissingCredential as exc:
        return _missing(Plane.MANAGER, exc, "fmg_list_policy_packages")


@mcp.tool()
async def fmg_get_policy_package(adom: str, package: str) -> dict:
    """Ordered rules in a policy package: position, action, enabled state, object refs."""
    try:
        return await mgr.get_policy_package(_jsonrpc(Plane.MANAGER), adom, package)
    except MissingCredential as exc:
        return _missing(Plane.MANAGER, exc, "fmg_get_policy_package")


@mcp.tool()
async def fmg_search_rules(
    adom: str, package: str, src: str = "", dst: str = "",
    service: str = "", object_name: str = "",
) -> dict:
    """Find rules by source, destination, service or object reference."""
    try:
        return await mgr.search_rules(
            _jsonrpc(Plane.MANAGER), adom, package,
            src or None, dst or None, service or None, object_name or None,
        )
    except MissingCredential as exc:
        return _missing(Plane.MANAGER, exc, "fmg_search_rules")


@mcp.tool()
async def fmg_resolve_object(adom: str, name: str, obj_type: str = "address") -> dict:
    """Resolve an address/service object or group to its members, RECURSIVELY.

    A rule reported only by object name is not an audit.
    """
    try:
        return await mgr.resolve_object(_jsonrpc(Plane.MANAGER), adom, name, obj_type)
    except MissingCredential as exc:
        return _missing(Plane.MANAGER, exc, "fmg_resolve_object")


@mcp.tool()
async def fmg_get_revisions(adom: str, package: str) -> dict:
    """Policy package revision history — the rollback context for a change review."""
    try:
        return await mgr.get_revisions(_jsonrpc(Plane.MANAGER), adom, package)
    except MissingCredential as exc:
        return _missing(Plane.MANAGER, exc, "fmg_get_revisions")


@mcp.tool()
async def fmg_preview_install(adom: str, package: str, target: str = "") -> dict:
    """Preview what installing a policy package WOULD change. Read-only, no gates."""
    try:
        return await mgr.preview_install(_jsonrpc(Plane.MANAGER), adom, package, target or None)
    except MissingCredential as exc:
        return _missing(Plane.MANAGER, exc, "fmg_preview_install")


# ---------------------------------------------------------------------------
# Analyzer plane — FortiAnalyzer (4 tools)
# ---------------------------------------------------------------------------

@mcp.tool()
async def faz_query_logs(
    adom: str, filter_expr: str, window_start: str = "",
    window_end: str = "", limit: int = 100, offset: int = 0,
) -> dict:
    """Query FortiAnalyzer traffic logs in a bounded window.

    An empty result means NO LOGS MATCHED IN THIS WINDOW — not that the traffic
    never happened. Defaults to the last 24 hours and says so.
    """
    try:
        return await az.query_logs(
            _jsonrpc(Plane.ANALYZER), adom, filter_expr,
            window_start or None, window_end or None, limit, offset,
        )
    except MissingCredential as exc:
        return _missing(Plane.ANALYZER, exc, "faz_query_logs")


@mcp.tool()
async def faz_fetch_more(
    adom: str, filter_expr: str, window_start: str, window_end: str,
    offset: int, limit: int = 100,
) -> dict:
    """Next page of a log query, re-run at an offset (FortiAnalyzer task ids are single-use)."""
    try:
        return await az.fetch_more(
            _jsonrpc(Plane.ANALYZER), adom, filter_expr,
            window_start, window_end, offset, limit,
        )
    except MissingCredential as exc:
        return _missing(Plane.ANALYZER, exc, "faz_fetch_more")


@mcp.tool()
async def faz_policy_activity(
    adom: str, policyid: int, window_start: str = "", window_end: str = "",
) -> dict:
    """Did anything match this policy in the window?

    'No' means no logs matched in that window. It is NOT evidence the rule is
    unused — check log forwarding and retention before concluding a rule is dead.
    """
    try:
        return await az.policy_activity(
            _jsonrpc(Plane.ANALYZER), adom, policyid,
            window_start or None, window_end or None,
        )
    except MissingCredential as exc:
        return _missing(Plane.ANALYZER, exc, "faz_policy_activity")


@mcp.tool()
async def faz_list_devices(adom: str) -> dict:
    """Devices forwarding logs to this FortiAnalyzer. Check before trusting an empty query."""
    try:
        return await az.list_devices(_jsonrpc(Plane.ANALYZER), adom)
    except MissingCredential as exc:
        return _missing(Plane.ANALYZER, exc, "faz_list_devices")


# ---------------------------------------------------------------------------
# Write path — 2 tools, disabled by default, two independent gates
# ---------------------------------------------------------------------------

@mcp.tool()
async def fmg_check_change_record(change_request: str) -> dict:
    """Check whether a ServiceNow change record is approved. Read-only."""
    result = await gates.check_change_request(change_request)
    return emit(
        Plane.MANAGER, source="servicenow", scope={"adom": "<n/a>"},
        data={"change_request": change_request, "approved": result.allowed,
              "posture": gates.describe()},
        outcome=Outcome.OK if result.allowed else result.outcome,
        message=result.message, tool="fmg_check_change_record",
    )


@mcp.tool()
async def fmg_install_package(
    adom: str, package: str, target: str,
    approved_by: str = "", change_request: str = "", is_lab: bool = False,
) -> dict:
    """Install a policy package to a device. PRODUCTION CHANGE EXECUTION.

    Requires BOTH an explicit human approval (`approved_by`) AND an approved
    ServiceNow change record (`change_request`). These are distinct gates and
    neither substitutes for the other. Disabled entirely unless
    FORTINET_ALLOW_WRITES=true.

    Use fmg_preview_install first — it shows what would change and needs no gate.
    """
    tool = "fmg_install_package"
    verdict = await gates.evaluate(
        approved_by=approved_by or None,
        change_request=change_request or None,
        is_lab=is_lab,
    )
    if not verdict.allowed:
        return emit(
            Plane.MANAGER, source="<gated>", scope={"adom": adom, "package": package},
            outcome=verdict.outcome, message=verdict.message,
            data={"posture": gates.describe()},
            notes=["Nothing was changed."], tool=tool,
        )

    try:
        client = _jsonrpc(Plane.MANAGER)
    except MissingCredential as exc:
        return _missing(Plane.MANAGER, exc, tool)

    # Principle II: identify the rollback revision BEFORE applying, not after failing.
    baseline = await mgr.get_revisions(client, adom, package)
    revisions = baseline.get("data", {}).get("revisions") or []
    rollback_to = revisions[0].get("version") if revisions else None

    try:
        result = await client.call(
            "exec", "/securityconsole/install/package",
            adom=adom, pkg=package, scope=[{"name": target}],
        )
    except Exception as exc:  # noqa: BLE001 - reported, never swallowed
        return emit(
            Plane.MANAGER, source=client.source, scope={"adom": adom, "package": package},
            outcome=Outcome.EMPTY_RESULT,
            message=f"Install failed: {exc}",
            data={"rollback_revision": rollback_to}, tool=tool,
        )

    return emit(
        Plane.MANAGER, source=client.source, scope={"adom": adom, "package": package},
        data={"install": result, "target": target,
              "rollback_revision": rollback_to, "gate_result": verdict.message},
        notes=["Verify device state against intent with fgt_compare_with_manager "
               "(Principle VIII)."],
        tool=tool,
    )


@mcp.tool()
async def fortinet_posture() -> dict:
    """Report which planes are configured and the current write-gate posture."""
    from credentials import configured_planes
    planes = [p.value for p in configured_planes()]
    return emit(
        Plane.MANAGER, source="fortinet-mcp", scope={"adom": "<n/a>"},
        data={
            "configured_planes": planes,
            "unconfigured_planes": [p.value for p in Plane if p.value not in planes],
            "write_posture": gates.describe(),
        },
        notes=["A plane that is not configured is not consulted, and NetClaw will "
               "say so rather than answering from another plane."],
        tool="fortinet_posture",
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
