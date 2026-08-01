"""Normalized cross-vendor facts via NAPALM getters.

Spec 076 FR-006, FR-007, FR-008. Contract:
specs/076-multivendor-cli-driver/contracts/mcp-tools.md

This is the one capability no other NetClaw server can provide. `pyATS` and
`junos-mcp` each answer well for their own platform, but their output shapes
differ — so "compare BGP neighbours across Cisco AND Arista AND Nokia" currently
requires reconciling three shapes by hand. NAPALM returns one shape, which is why
FR-008 permits this server to answer normalized reads **even on platforms owned by
another server**, read-only.

Two rules that matter more than the plumbing:

1. **An unavailable getter is REPORTED, never omitted** (FR-007). NAPALM driver
   coverage is genuinely uneven — a driver may implement `get_facts` but not
   `get_bgp_neighbors`. Silently dropping the missing one turns "this platform
   cannot tell us" into "there are none", which is a wrong answer rather than a
   missing one.

2. **A template-parsed result is NEVER presented as a normalized fact.** Where no
   NAPALM driver exists at all — SR Linux, FRR, VyOS, MikroTik — the honest answer
   is `available: false` with a reason, plus a pointer to `run_command`. Scraping
   CLI output and labelling it normalized would produce a normalized-*looking*
   answer of lower reliability, which is the exact failure FR-007 exists to
   prevent.

Verified against live IOS-XE (NAPALM `ios`, getters return real data) and live
Nokia SR Linux (no driver, gap reported explicitly).
"""

from __future__ import annotations

import os

import routing
from credentials import CredentialError, resolve as resolve_credential
from inventory import sources as inv

SERVER_ID = "multivendor-cli"
DEFAULT_TIMEOUT = int(os.environ.get("MULTIVENDOR_TIMEOUT_S", "30"))

# Platform identifier -> NAPALM driver name. Only platforms NAPALM genuinely
# supports appear here; everything else is a deliberate, reported gap.
NAPALM_DRIVER: dict[str, str] = {
    "cisco_ios": "ios",
    "cisco_xe": "ios",
    "cisco_iosxe": "ios",
    "cisco_nxos": "nxos_ssh",
    "cisco_xr": "iosxr",
    "juniper_junos": "junos",
    "arista_eos": "eos",
}

# Platforms known to have NO NAPALM driver, with the reason stated so the gap is
# informative rather than a bare failure. Anything absent from both maps gets a
# generic "no driver" message.
KNOWN_NO_DRIVER: dict[str, str] = {
    "nokia_srl": "NAPALM has no SR Linux driver; use run_command, or gNMI for structured data",
    "nokia_sros": "NAPALM has no SR OS driver; use run_command",
    "frr": "NAPALM has no FRR driver; use run_command with vtysh",
    "linux": "NAPALM has no generic Linux driver; use run_command",
    "vyos": "NAPALM has no VyOS driver; use run_command",
    "mikrotik_routeros": "NAPALM has no RouterOS driver; use run_command",
    "dell_sonic": "NAPALM has no SONiC driver; use run_command",
    "extreme_exos": "NAPALM has no EXOS driver; use run_command",
    "huawei_vrp": "NAPALM has no VRP driver; use run_command",
    "ubiquiti_edge": "NAPALM has no EdgeOS driver; use run_command",
}

# Getters exposed. A conservative, read-only subset — every one is a pure read.
SUPPORTED_GETTERS: tuple[str, ...] = (
    "get_facts",
    "get_interfaces",
    "get_interfaces_ip",
    "get_bgp_neighbors",
    "get_lldp_neighbors",
    "get_arp_table",
    "get_environment",
    "get_users",
    "get_network_instances",
)


def _gap(getter: str, reason: str) -> dict:
    return {"getter": getter, "available": False, "data": None,
            "gap_reason": reason, "provenance": None}


def get_facts(device: str, getters: list[str] | None = None,
              timeout_s: int | None = None) -> dict:
    """Retrieve normalized facts. Gaps are reported, never silently omitted."""
    getters = getters or ["get_facts", "get_interfaces"]
    timeout_s = timeout_s or DEFAULT_TIMEOUT

    try:
        res = inv.resolve()
        dev = inv.find(res.devices, device)
    except inv.InventoryError as exc:
        return {"server": SERVER_ID, "device": device, "status": "not_found",
                "error": str(exc)}

    platform = (dev.platform or "").lower()
    base = {
        "server": SERVER_ID,
        "device": device,
        "platform": dev.platform,
        "source": res.source.value,
        "owning_server": routing.owner_of(dev.platform),
    }

    # FR-008: normalized reads are permitted even on platforms another server
    # owns. This is the deliberate exception, and it is read-only.
    decision = routing.route(dev.platform, routing.Operation.NORMALIZED_READ)
    if decision.refused:  # pragma: no cover - normalized reads are never refused today
        payload = routing.refusal_payload(device, dev.platform, decision)
        payload.update(base)
        return payload

    unknown = [g for g in getters if g not in SUPPORTED_GETTERS]
    if unknown:
        return {**base, "status": "error",
                "error": f"unsupported getter(s) {unknown}; "
                         f"available: {', '.join(SUPPORTED_GETTERS)}"}

    driver_name = NAPALM_DRIVER.get(platform)
    if driver_name is None:
        # No NAPALM driver: report every requested getter as an explicit gap.
        reason = KNOWN_NO_DRIVER.get(
            platform, f"no NAPALM driver for platform {dev.platform!r}; use run_command")
        return {**base, "status": "ok", "napalm_driver": None,
                "facts": [_gap(g, reason) for g in getters],
                "note": "platform has no NAPALM driver — these are reported gaps, "
                        "not empty results (FR-007)"}

    try:
        cred = resolve_credential(dev.credential_ref)
    except CredentialError as exc:
        return {**base, "status": "auth_failed", "error": str(exc)}

    from napalm import get_network_driver

    driver = get_network_driver(driver_name)
    conn = driver(
        hostname=dev.hostname,
        username=cred.username,
        password=cred.password or "",
        optional_args={"secret": cred.enable or "", "conn_timeout": min(timeout_s, 30)},
        timeout=timeout_s,
    )
    try:
        conn.open()
    except Exception as exc:  # noqa: BLE001
        return {**base, "status": "unreachable", "napalm_driver": driver_name,
                "error": f"{type(exc).__name__}: {str(exc)[:260]}"}

    facts = []
    for getter in getters:
        fn = getattr(conn, getter, None)
        if fn is None or not callable(fn):
            facts.append(_gap(getter, f"driver {driver_name!r} does not implement {getter}"))
            continue
        try:
            facts.append({"getter": getter, "available": True, "data": fn(),
                          "gap_reason": None, "provenance": "napalm"})
        except NotImplementedError:
            # The common real case: the driver exists but this getter does not.
            facts.append(_gap(getter, f"driver {driver_name!r} does not implement {getter}"))
        except Exception as exc:  # noqa: BLE001
            facts.append(_gap(getter, f"{type(exc).__name__}: {str(exc)[:180]}"))

    try:
        conn.close()
    except Exception:  # noqa: BLE001 - close failures must not mask results
        pass

    return {**base, "status": "ok", "napalm_driver": driver_name,
            "credential_path": cred.path.value, "facts": facts}
