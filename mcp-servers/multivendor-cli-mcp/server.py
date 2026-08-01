#!/usr/bin/env python3
"""Multivendor CLI Driver — MCP server entry point.

Spec 076 (roadmap R1). Contract:
specs/076-multivendor-cli-driver/contracts/mcp-tools.md

Gives NetClaw a general "connect to this device and ask it something" capability.
Before this server, all four device-facing servers were platform-bound — pyATS
(Cisco), junos-mcp (Juniper), gnmi-mcp (telemetry only), radkit-mcp
(cloud-relayed) — leaving ~90 platform families unreachable: MikroTik, VyOS,
SONiC, Nokia SR Linux, Extreme, Huawei, Dell, Ubiquiti EdgeOS.

ROUTING — this server is NOT a replacement for pyATS or junos-mcp:

  Cisco IOS/XE/NXOS/XR ......... pyATS       (far richer, ~2000 Genie parsers)
  Juniper Junos ................ junos-mcp   (PyEZ/NETCONF)
  Streaming telemetry .......... gnmi-mcp
  No direct reachability ....... radkit-mcp
  Everything else .............. THIS SERVER
  Cross-vendor normalized reads. THIS SERVER (read-only, even on the above)

Writes stay single-pathed per platform: this server REFUSES configuration change
on platforms owned by another server (FR-010). That is what keeps Principles I
and VIII enforceable — "verified by which tool?" must have one answer.

MUST run from this server's dedicated virtualenv. `napalm`/`netmiko` resolve
cryptography 49.x while the system interpreter carries 46.x, which NetClaw's
NCFED federation stack uses for X.509 issuance (spec 060). Running this outside
its venv risks the certificate stack, not this server (FR-030a, research R7).

STATUS: stub. Created early per analyze finding O1 — the tool implementations
land in later phases, but without an entry point none of them would be reachable
over MCP, so no story phase would be independently testable as an MCP capability.
Tools are registered here as they are implemented.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.fastmcp import FastMCP  # noqa: E402

import routing  # noqa: E402
from credentials import CredentialError, resolve as resolve_credential  # noqa: E402
from inventory import sources as inv  # noqa: E402
from policy.filter import Mode, evaluate  # noqa: E402
from tools import facts as fact_tools  # noqa: E402
from tools import change as change_tools  # noqa: E402
from tools import fleet as fleet_tools  # noqa: E402
from tools import raw as raw_tools  # noqa: E402
from policy.platform_deny import (  # noqa: E402
    PLATFORM_DENY,
    READ_ONLY_PREFIXES,
    is_modelled,
)

SERVER_NAME = "multivendor-cli"          # the `server` field in every result (FR-011)
SERVER_VERSION = "0.1.0"

mcp = FastMCP("multivendor-cli-mcp")


def write_enabled() -> bool:
    """Whether write tools are exposed at all (FR-022).

    Default is read-only. Write tools are ABSENT from tools/list rather than
    present-and-refusing, so an agent cannot even attempt a change unless an
    operator has deliberately opted in.
    """
    return os.environ.get("MULTIVENDOR_WRITE_ENABLED", "").lower() in ("1", "true", "yes")


def current_mode() -> Mode:
    return Mode.WRITE_ENABLED if write_enabled() else Mode.READ_ONLY


@mcp.tool()
def server_info() -> dict:
    """Report this server's identity, mode, and platform-policy coverage.

    Deliberately the first tool implemented: it lets an operator confirm the
    safety posture (read-only vs write-enabled) and see which platforms have
    explicit destructive-syntax modelling, before trusting it with a device.
    """
    return {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "mode": current_mode().value,
        "write_enabled": write_enabled(),
        "modelled_platforms": sorted(PLATFORM_DENY),
        "read_only_prefixes": sorted(READ_ONLY_PREFIXES),
        "routing": {
            "owned_elsewhere": {
                "cisco_ios": "pyats", "cisco_xe": "pyats",
                "cisco_nxos": "pyats", "cisco_xr": "pyats",
                "juniper_junos": "junos-mcp",
            },
            "note": (
                "Reads may overlap with the owning server; writes may not. "
                "Cross-vendor normalized reads are permitted everywhere, read-only."
            ),
        },
        "status": "stub — tool surface lands in spec 076 Phases 3-6",
    }


@mcp.tool()
def check_command_policy(command: str, platform: str | None = None) -> dict:
    """Evaluate a command against policy WITHOUT contacting any device.

    Lets an operator (or the agent) find out whether a command would be permitted
    before anything is attempted, and see which rule would reject it. Enforcement
    itself is server-side and unavoidable (FR-029); this only makes it inspectable.
    """
    verdict = evaluate(command, platform, current_mode())
    return {
        "server": SERVER_NAME,
        "command": command,
        "platform": platform,
        "mode": current_mode().value,
        "allowed": verdict.allowed,
        "rule": verdict.rule.value if verdict.rule else None,
        "denied_reason": verdict.denied_reason,
        "platform_modelled": is_modelled(platform),
        "note": (
            None if is_modelled(platform)
            else "platform has no explicit destructive-syntax model; "
                 "universal denylist still applies"
        ),
    }


@mcp.tool()
def list_devices(group: str | None = None, platform: str | None = None) -> dict:
    """List devices from the configured inventory, with source attribution.

    Reports which of the three inventory sources answered, and why it was not the
    preferred one when it was not (FR-017c) — so a stale cache is never mistaken
    for live data. Never returns credential values.
    """
    try:
        res = inv.resolve()
    except inv.InventoryError as exc:
        return {"server": SERVER_NAME, "status": "error", "error": str(exc)}

    devices = res.devices
    if group:
        devices = [d for d in devices if group in d.groups]
    if platform:
        devices = [d for d in devices if d.platform == platform]

    return {
        "server": SERVER_NAME,
        "source_used": res.source.value,
        "fallback_reason": res.fallback_reason,
        "count": len(devices),
        "devices": [d.public() for d in devices],
    }


@mcp.tool()
def check_device_readiness(device: str) -> dict:
    """Check whether a device could be acted on, WITHOUT contacting it.

    Resolves the device from inventory, resolves its credential reference, and
    applies the routing rule — reporting which server owns the platform and
    whether this one may read or write it. Deliberately contacts nothing: it
    answers "is this wired up correctly" before any session is opened.
    """
    try:
        res = inv.resolve()
        dev = inv.find(res.devices, device)
    except inv.InventoryError as exc:
        return {"server": SERVER_NAME, "device": device, "status": "not_found",
                "error": str(exc)}

    cred_posture, cred_error = None, None
    try:
        cred_posture = resolve_credential(dev.credential_ref).posture()
    except CredentialError as exc:
        cred_error = str(exc)

    read = routing.route(dev.platform, routing.Operation.NORMALIZED_READ)
    raw = routing.route(dev.platform, routing.Operation.RAW_READ)
    write = routing.route(dev.platform, routing.Operation.WRITE)

    return {
        "server": SERVER_NAME,
        "device": dev.public(),
        "source_used": res.source.value,
        "credentials": cred_posture,
        "credential_error": cred_error,
        "routing": {
            "owning_server": read.owning_server,
            "normalized_read_permitted": read.permitted,
            "raw_read_permitted": raw.permitted,
            "write_permitted": write.permitted,
            "write_refused_reason": write.reason,
        },
        "ready": cred_error is None,
    }


@mcp.tool()
def run_command(device: str, command: str, timeout_s: int | None = None) -> dict:
    """Execute a read-only command on a device and return its output.

    The command is filtered server-side BEFORE any connection is opened, so a
    denied command never establishes a session. Failure statuses stay distinct —
    unreachable, auth_failed, platform_mismatch, denied, timeout — because each
    needs a different fix.

    Refuses raw execution on platforms owned by pyATS or junos-mcp, naming the
    correct server.
    """
    return raw_tools.run_command(device, command, timeout_s)


@mcp.tool()
def check_reachability(device: str) -> dict:
    """Probe a device, separating unreachable from auth-failed from wrong-platform.

    The right first call on a newly added device: those three failures look
    identical in a generic error and need three different remedies.
    """
    return raw_tools.check_reachability(device)


@mcp.tool()
def get_facts(device: str, getters: list[str] | None = None,
              timeout_s: int | None = None) -> dict:
    """Retrieve normalized operational facts in one shape across vendors.

    This is the capability no other NetClaw server provides: pyATS and junos-mcp
    each answer well for their own platform, but their shapes differ, so
    cross-vendor questions need manual reconciliation. NAPALM returns one shape.

    Permitted read-only even on Cisco and Juniper, which is the deliberate
    exception to platform-first routing.

    Where a platform has no NAPALM driver — SR Linux, FRR, VyOS, MikroTik — every
    requested getter is returned as an explicit gap with a reason, never silently
    omitted. An absent getter and an empty result are different answers.
    """
    return fact_tools.get_facts(device, getters, timeout_s)


@mcp.tool()
def run_fleet(target: str, command: str | None = None,
              getters: list[str] | None = None,
              max_workers: int | None = None,
              timeout_s: int | None = None) -> dict:
    """Run one query across a group of devices, concurrently.

    `target` is a group name, a comma-separated device list, or "all". Supply
    exactly one of `command` (raw) or `getters` (normalized).

    Every targeted device appears in the results, including failures — a silently
    absent device would read as success, which is the most dangerous possible
    output for a fleet query. One device failing never aborts the others.
    """
    return fleet_tools.run_fleet(target, command, getters, max_workers, timeout_s)


if write_enabled():
    # Registered ONLY when write mode is enabled (FR-022): absent from tools/list
    # otherwise, so an agent cannot attempt a change that was never sanctioned.
    @mcp.tool()
    def apply_config(device: str, config: str, change_request: str | None = None,
                     approved_by: str | None = None) -> dict:
        """Apply configuration, only if every gate is satisfied.

        Gates, in order, each returning before the next is considered:
        routing -> command filter -> lab/production classification -> ServiceNow
        change request (production only) -> explicit human approval -> baseline
        capture.

        A production change requires BOTH an approved ServiceNow change request
        and human approval — they are distinct gates. An unclassified device is
        treated as production, never assumed to be lab.

        Refuses outright on Cisco and Juniper: writes are single-pathed per
        platform.
        """
        return change_tools.apply_config(device, config, change_request, approved_by)


    @mcp.tool()
    def check_change_request(change_request: str) -> dict:
        """Check whether a ServiceNow change request authorises implementation."""
        return change_tools.check_change_request(change_request)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
