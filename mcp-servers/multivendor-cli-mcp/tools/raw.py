"""Raw command execution against a device.

Spec 076 FR-002 through FR-005, FR-029. Contract:
specs/076-multivendor-cli-driver/contracts/mcp-tools.md

The path this module implements, in order, and the order is the contract:

    inventory -> routing -> FILTER -> credentials -> connect -> execute

The filter runs **before** credentials are resolved and before any socket is
opened (FR-029). A denied command must never establish a session — otherwise
"read-only" means "we connected and then decided not to", which is not the same
guarantee at all.

The five failure statuses are kept distinct (FR-005) because each has a different
remediation, and collapsing them wastes an operator's time:

    unreachable        network/port problem
    auth_failed        credentials resolved but rejected
    platform_mismatch  inventory says one platform, device is another
    denied             policy refused it; no session was opened
    timeout            device accepted but did not answer in time

Verified end-to-end against a live FRR container: legitimate reads returned real
output, while `vtysh -c "configure terminal"`, `vtysh -c "reload"`,
`vtysh -c "show version"; reload` and `rm -rf /` were all refused without the
device being contacted.
"""

from __future__ import annotations

import os

import routing
from credentials import CredentialError, resolve as resolve_credential
from inventory import sources as inv
from policy.filter import Mode, evaluate

SERVER_ID = "multivendor-cli"

DEFAULT_TIMEOUT = int(os.environ.get("MULTIVENDOR_TIMEOUT_S", "30"))

# Platform identifier -> netmiko device_type. Kept explicit rather than passing
# the inventory string straight through, so a typo in inventory surfaces as an
# unsupported-platform error (FR-003) instead of an obscure netmiko failure.
NETMIKO_DRIVER: dict[str, str] = {
    "nokia_srl": "nokia_srl",
    "nokia_sros": "nokia_sros",
    "vyos": "vyos",
    "mikrotik_routeros": "mikrotik_routeros",
    "dell_sonic": "dell_sonic",
    "edgecore_sonic": "edgecore_sonic",
    "dell_os10": "dell_os10",
    "extreme_exos": "extreme_exos",
    "huawei_vrp": "huawei_vrp",
    "ubiquiti_edge": "ubiquiti_edge",
    "arista_eos": "arista_eos",
    "cumulus_linux": "cumulus_linux",
    # FRR and other Linux-hosted NOSes: netmiko's `linux` driver reaches a shell,
    # and the router CLI is entered per-command via a wrapper such as
    # `vtysh -c "show ip route"`. The filter unwraps that wrapper and judges the
    # inner command, so the wrapper cannot be used as a config escape.
    "linux": "linux",
    "frr": "linux",
}


def _result(device: str, platform: str | None, command: str, status: str, **extra) -> dict:
    out = {
        "server": SERVER_ID,
        "device": device,
        "platform": platform,
        "command": command,
        "status": status,
    }
    out.update(extra)
    return out


def run_command(device: str, command: str, timeout_s: int | None = None) -> dict:
    """Execute one command on one device, or explain precisely why not."""
    timeout_s = timeout_s or DEFAULT_TIMEOUT
    write_mode = os.environ.get("MULTIVENDOR_WRITE_ENABLED", "").lower() in ("1", "true", "yes")
    mode = Mode.WRITE_ENABLED if write_mode else Mode.READ_ONLY

    # --- inventory ---
    try:
        res = inv.resolve()
        dev = inv.find(res.devices, device)
    except inv.InventoryError as exc:
        return _result(device, None, command, "not_found", error=str(exc))

    # --- routing: is this platform ours to run raw commands against? ---
    decision = routing.route(dev.platform, routing.Operation.RAW_READ)
    if decision.refused:
        payload = routing.refusal_payload(device, dev.platform, decision)
        payload.update({"command": command, "source": res.source.value})
        return payload

    # --- driver support (FR-003) ---
    driver = NETMIKO_DRIVER.get((dev.platform or "").lower())
    if driver is None:
        return _result(
            device, dev.platform, command, "platform_mismatch",
            source=res.source.value,
            error=(f"platform {dev.platform!r} has no supported driver mapping. "
                   f"Known: {', '.join(sorted(NETMIKO_DRIVER))}"),
        )

    # --- FILTER, before credentials and before any socket (FR-029) ---
    verdict = evaluate(command, dev.platform, mode)
    if not verdict.allowed:
        return _result(
            device, dev.platform, command, "denied",
            source=res.source.value,
            denied_reason=verdict.denied_reason,
            note="no session was opened — the command was refused before connecting",
        )

    # --- credentials ---
    try:
        cred = resolve_credential(dev.credential_ref)
    except CredentialError as exc:
        return _result(device, dev.platform, command, "auth_failed",
                       source=res.source.value, error=str(exc))

    # --- connect and execute ---
    from netmiko import ConnectHandler
    from netmiko.exceptions import (
        NetmikoAuthenticationException,
        NetmikoTimeoutException,
    )

    params = {
        "device_type": driver,
        "host": dev.hostname,
        "username": cred.username,
        "password": cred.password,
        "secret": cred.enable or "",
        "conn_timeout": min(timeout_s, 30),
        "auth_timeout": min(timeout_s, 30),
        "fast_cli": False,
    }
    port = os.environ.get(f"MULTIVENDOR_{device.replace('-', '_').upper()}_PORT")
    if port:
        params["port"] = int(port)

    try:
        conn = ConnectHandler(**params)
    except NetmikoAuthenticationException as exc:
        return _result(device, dev.platform, command, "auth_failed",
                       source=res.source.value,
                       credential_path=cred.path.value, error=str(exc)[:300])
    except NetmikoTimeoutException as exc:
        return _result(device, dev.platform, command, "unreachable",
                       source=res.source.value, error=str(exc)[:300])
    except Exception as exc:  # noqa: BLE001 - any connect failure is unreachable
        return _result(device, dev.platform, command, "unreachable",
                       source=res.source.value,
                       error=f"{type(exc).__name__}: {str(exc)[:260]}")

    try:
        output = conn.send_command(command, read_timeout=timeout_s)
    except Exception as exc:  # noqa: BLE001
        conn.disconnect()
        return _result(device, dev.platform, command, "timeout",
                       source=res.source.value,
                       error=f"{type(exc).__name__}: {str(exc)[:260]}")

    conn.disconnect()
    return _result(
        device, dev.platform, command, "ok",
        source=res.source.value,
        credential_path=cred.path.value,
        driver=driver,
        output=output,
    )


def check_reachability(device: str) -> dict:
    """Separate unreachable from auth_failed from platform_mismatch (FR-005).

    The right first call on a newly added device, because those three look
    identical in a generic failure message and need three different fixes.
    """
    try:
        res = inv.resolve()
        dev = inv.find(res.devices, device)
    except inv.InventoryError as exc:
        return {"server": SERVER_ID, "device": device, "status": "not_found",
                "error": str(exc)}

    driver = NETMIKO_DRIVER.get((dev.platform or "").lower())
    base = {
        "server": SERVER_ID,
        "device": device,
        "source": res.source.value,
        "platform_expected": dev.platform,
        "driver": driver,
        "owning_server": routing.owner_of(dev.platform),
    }
    if driver is None:
        return {**base, "tcp": False, "auth": False, "status": "platform_mismatch",
                "error": f"no driver mapping for platform {dev.platform!r}"}

    # A reachability probe is a read-only diagnostic, so it uses the safest
    # possible command the platform supports rather than anything operator-supplied.
    probe = 'vtysh -c "show version"' if driver == "linux" else "show version"
    result = run_command(device, probe)
    status_map = {"ok": "ok", "auth_failed": "auth_failed",
                  "unreachable": "unreachable", "timeout": "unreachable",
                  "platform_mismatch": "platform_mismatch", "denied": "denied"}
    return {
        **base,
        "tcp": result["status"] not in ("unreachable",),
        "auth": result["status"] == "ok",
        "status": status_map.get(result["status"], result["status"]),
        "probe": probe,
        "error": result.get("error") or result.get("denied_reason"),
    }
