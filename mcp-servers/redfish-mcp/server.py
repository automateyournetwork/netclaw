#!/usr/bin/env python3
"""redfish-mcp — out-of-band hardware visibility via Redfish (read-only). Roadmap R15.

Answers the question NetClaw could not answer at all: **"is the box dead, or is it the
network?"** A BMC is the only vantage point that can tell those apart, because it answers when
the operating system cannot.

Read-only, and enforced at the transport: `client.py` issues nothing but GET. Redfish exposes
`#ComputerSystem.Reset` as a POST on every system, and a power cycle on the wrong box is an
outage, so there is no code path here that can issue one.

Every response that mentions host power or health carries a **verdict** stating what the reading
does and does not establish, and `verdict.emit()` raises rather than emit a host claim without
one. The reason is that the distinction is symmetric and each direction is a different wrong
answer:

    BMC unreachable      -> nothing was learned about the host (NOT "the host is down")
    BMC reachable, Off   -> the host IS off; a fact, and the whole point of out-of-band
    BMC reachable, On    -> the host has power; the OS may still be hung

Built rather than adopted: `carlosedp/redfish-mcp-server` has no license file at all and
`fredriksknese/mcp-redfish` resolves to NOASSERTION, neither of which is vendorable.
"""

from __future__ import annotations

import os
import sys

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import BmcUnreachable, RedfishClient  # noqa: E402
from verdict import (VerdictError, emit, host_verdict,  # noqa: E402
                     unreachable_verdict)

mcp = FastMCP("redfish-mcp")

ROOT = "/redfish/v1"


def _client(endpoint: str | None):
    return RedfishClient(base_url=endpoint)


def _gaps(c: RedfishClient) -> list[str] | None:
    note = c.tls_note()
    return [note] if note else None


@mcp.tool()
def redfish_status(endpoint: str | None = None) -> dict:
    """Check whether the BMC answers, and what that does and does not tell you.

    Call this first. It is the only tool that distinguishes "the BMC is unreachable" from "the
    host is off" — a distinction every other reading depends on, and the reason this server
    exists.
    """
    try:
        c = _client(endpoint)
    except BmcUnreachable as exc:
        return emit("redfish_status", error=str(exc))
    try:
        root = c.get(ROOT)
    except BmcUnreachable as exc:
        return emit("redfish_status", endpoint=c.base,
                    verdict=unreachable_verdict(str(exc)),
                    host_claim={"state": "UNKNOWN"}, gaps=_gaps(c))
    return emit("redfish_status", endpoint=c.base,
                data={"service_root": root.get("Name"),
                      "redfish_version": root.get("RedfishVersion"),
                      "vendor_oem": list((root.get("Oem") or {}).keys()),
                      "collections": sorted(k for k, v in root.items()
                                            if isinstance(v, dict) and "@odata.id" in v),
                      "authenticated": bool(c.user)},
                gaps=_gaps(c))


@mcp.tool()
def redfish_systems(endpoint: str | None = None) -> dict:
    """Report each computer system's power state, hardware health, CPU and memory summary.

    This is the "is the box dead" answer. Every system carries a verdict saying what its power
    state establishes about the host — a `PowerState` of `On` is not a claim that the OS is up.
    """
    try:
        c = _client(endpoint)
    except BmcUnreachable as exc:
        return emit("redfish_systems", error=str(exc))
    try:
        paths = c.members(f"{ROOT}/Systems")
    except BmcUnreachable as exc:
        return emit("redfish_systems", endpoint=c.base,
                    verdict=unreachable_verdict(str(exc)),
                    host_claim={"state": "UNKNOWN"}, gaps=_gaps(c))

    systems = []
    worst = None
    for p in paths:
        try:
            s = c.get(p)
        except BmcUnreachable as exc:
            systems.append({"path": p, "error": str(exc)})
            continue
        status = s.get("Status") or {}
        v = host_verdict(s.get("PowerState"), status.get("Health") or status.get("HealthRollup"))
        if worst is None:
            worst = v
        systems.append({
            "id": s.get("Id"), "name": s.get("Name"),
            "manufacturer": s.get("Manufacturer"), "model": s.get("Model"),
            "serial": s.get("SerialNumber"), "bios_version": s.get("BiosVersion"),
            "power_state": s.get("PowerState"),
            "status": status,
            "processors": s.get("ProcessorSummary"),
            "memory": s.get("MemorySummary"),
            "verdict": v,
        })
    return emit("redfish_systems", endpoint=c.base,
                verdict=worst or unreachable_verdict("no systems returned"),
                host_claim=systems,
                data={"count": len(systems)}, gaps=_gaps(c))


@mcp.tool()
def redfish_thermal_power(endpoint: str | None = None) -> dict:
    """Report chassis temperatures, fans, power consumption and PSU state.

    Thermal and power readings are hardware facts and say nothing about the OS. A chassis can be
    thermally healthy while the host is hung, and a fan fault does not mean the box is down.
    """
    try:
        c = _client(endpoint)
    except BmcUnreachable as exc:
        return emit("redfish_thermal_power", error=str(exc))
    try:
        paths = c.members(f"{ROOT}/Chassis")
    except BmcUnreachable as exc:
        return emit("redfish_thermal_power", endpoint=c.base,
                    verdict=unreachable_verdict(str(exc)), gaps=_gaps(c))

    out = []
    for p in paths:
        entry: dict = {"path": p}
        for sub, key in (("Thermal", "thermal"), ("Power", "power")):
            try:
                body = c.get(f"{p}/{sub}")
            except BmcUnreachable as exc:
                # Vendors implement different subsets; an absent subresource is a coverage gap,
                # not a fault, and must not read as "no thermal problem".
                entry[key] = {"unavailable": str(exc)}
                continue
            if sub == "Thermal":
                entry[key] = {
                    "temperatures": [{"name": t.get("Name"),
                                      "celsius": t.get("ReadingCelsius"),
                                      "upper_critical": t.get("UpperThresholdCritical"),
                                      "health": (t.get("Status") or {}).get("Health")}
                                     for t in (body.get("Temperatures") or [])],
                    "fans": [{"name": f.get("Name"), "reading": f.get("Reading"),
                              "units": f.get("ReadingUnits"),
                              "health": (f.get("Status") or {}).get("Health")}
                             for f in (body.get("Fans") or [])],
                }
            else:
                entry[key] = {
                    "power_control": [{"name": pc.get("Name"),
                                       "consumed_watts": pc.get("PowerConsumedWatts"),
                                       "capacity_watts": pc.get("PowerCapacityWatts")}
                                      for pc in (body.get("PowerControl") or [])],
                    "supplies": [{"name": ps.get("Name"),
                                  "health": (ps.get("Status") or {}).get("Health"),
                                  "state": (ps.get("Status") or {}).get("State"),
                                  "input_watts": ps.get("PowerInputWatts")}
                                 for ps in (body.get("PowerSupplies") or [])],
                }
        out.append(entry)

    gaps = _gaps(c) or []
    gaps.append("Thermal and power are hardware readings. They establish nothing about whether "
                "the operating system is running.")
    return emit("redfish_thermal_power", endpoint=c.base,
                data={"chassis": out, "count": len(out)}, gaps=gaps)


@mcp.tool()
def redfish_managers(endpoint: str | None = None) -> dict:
    """Report the BMC's own firmware version, model and health.

    This describes the **BMC**, not the host. A healthy BMC on stale firmware is a real finding,
    and it is orthogonal to the state of the machine it manages.
    """
    try:
        c = _client(endpoint)
    except BmcUnreachable as exc:
        return emit("redfish_managers", error=str(exc))
    try:
        paths = c.members(f"{ROOT}/Managers")
    except BmcUnreachable as exc:
        return emit("redfish_managers", endpoint=c.base,
                    verdict=unreachable_verdict(str(exc)), gaps=_gaps(c))
    mgrs = []
    for p in paths:
        try:
            m = c.get(p)
        except BmcUnreachable as exc:
            mgrs.append({"path": p, "error": str(exc)}); continue
        mgrs.append({"id": m.get("Id"), "name": m.get("Name"),
                     "manager_type": m.get("ManagerType"),
                     "model": m.get("Model"),
                     "firmware_version": m.get("FirmwareVersion"),
                     "status": m.get("Status"),
                     "datetime": m.get("DateTime")})
    gaps = _gaps(c) or []
    gaps.append("These fields describe the BMC itself, not the host it manages.")
    return emit("redfish_managers", endpoint=c.base,
                data={"managers": mgrs, "count": len(mgrs)}, gaps=gaps)


@mcp.tool()
def redfish_firmware(endpoint: str | None = None) -> dict:
    """List firmware inventory from the UpdateService.

    An empty inventory means this BMC does not populate it — several vendors do not — never that
    the machine has no firmware.
    """
    try:
        c = _client(endpoint)
    except BmcUnreachable as exc:
        return emit("redfish_firmware", error=str(exc))
    try:
        inv = c.get(f"{ROOT}/UpdateService/FirmwareInventory")
    except BmcUnreachable as exc:
        return emit("redfish_firmware", endpoint=c.base,
                    data={"firmware": [], "count": 0},
                    gaps=[f"Firmware inventory not available: {exc}. Many BMCs do not populate "
                          "it; this is not evidence about the firmware itself."])
    items = []
    for ref in (inv.get("Members") or []):
        p = ref.get("@odata.id")
        if not p:
            continue
        try:
            f = c.get(p)
        except BmcUnreachable:
            continue
        items.append({"id": f.get("Id"), "name": f.get("Name"),
                      "version": f.get("Version"), "updateable": f.get("Updateable"),
                      "status": f.get("Status")})
    gaps = _gaps(c) or []
    if not items:
        gaps.append("Firmware inventory returned no entries. That means this BMC does not "
                    "populate it, not that the machine has no firmware.")
    return emit("redfish_firmware", endpoint=c.base,
                data={"firmware": items, "count": len(items)}, gaps=gaps)


@mcp.tool()
def redfish_logs(endpoint: str | None = None, limit: int = 50) -> dict:
    """Read BMC event/SEL log entries.

    An empty log is not a clean bill of health: SELs are ring buffers that are cleared on
    service, and severity filtering at the vendor means absence of entries is absence of
    *recorded* entries.
    """
    try:
        c = _client(endpoint)
    except BmcUnreachable as exc:
        return emit("redfish_logs", error=str(exc))
    entries: list[dict] = []
    services: list[str] = []
    try:
        for mgr in c.members(f"{ROOT}/Managers"):
            for svc in c.members(f"{mgr}/LogServices"):
                services.append(svc)
                try:
                    body = c.get(f"{svc}/Entries")
                except BmcUnreachable:
                    continue
                for e in (body.get("Members") or [])[:max(limit, 1)]:
                    entries.append({"id": e.get("Id"), "created": e.get("Created"),
                                    "severity": e.get("Severity"),
                                    "entry_type": e.get("EntryType"),
                                    "message": e.get("Message"),
                                    "resolved": e.get("Resolved")})
    except BmcUnreachable as exc:
        return emit("redfish_logs", endpoint=c.base,
                    verdict=unreachable_verdict(str(exc)), gaps=_gaps(c))
    gaps = _gaps(c) or []
    if not entries:
        gaps.append("No log entries returned. SELs are ring buffers cleared during service, so "
                    "this is absence of RECORDED events, not evidence that nothing happened.")
    return emit("redfish_logs", endpoint=c.base,
                data={"entries": entries[:max(limit, 1)], "count": len(entries),
                      "log_services": services,
                      "truncated": len(entries) > limit},
                gaps=gaps)


if __name__ == "__main__":
    mcp.run(transport="stdio")
