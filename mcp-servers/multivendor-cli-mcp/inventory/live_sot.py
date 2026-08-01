"""Live inventory from NetClaw's sources of truth.

Spec 076 FR-017 (live tier), T018.

Queried at call time so inventory **cannot drift** — which is why this is the
preferred tier. NetBox and Nautobot are read directly over their REST APIs rather
than through `nornir-netbox` / `nornir-nautobot`: those plugins build a Nornir
inventory object, and this server needs plain `Device` records that flow through
the same three-source attribution, credential-reference and secret-rejection path
as every other source. Using the plugins would mean two different Device shapes.

**Credentials are never read from a source of truth**, even though NetBox can
store them. Only a credential *reference* is derived, and the secret is resolved
at runtime from Vault or the environment (FR-017d, FR-019, Principle XIII).

Returns an empty list only when a source genuinely has no devices. An unreachable
source raises, so `auto` falls through to a file tier rather than silently
reporting an empty fleet — "no devices" and "cannot see the devices" must never
look the same (FR-017b/c).
"""

from __future__ import annotations

import os

from inventory.sources import Device, InventoryError, Source

# NetBox/Nautobot platform slugs vary per install, so map generously and fall back
# to the raw slug — the driver lookup will report an unsupported platform clearly
# (FR-003) rather than failing obscurely here.
PLATFORM_HINTS: dict[str, str] = {
    "ios": "cisco_ios", "iosxe": "cisco_xe", "cisco-ios": "cisco_ios",
    "cisco-iosxe": "cisco_xe", "nxos": "cisco_nxos", "iosxr": "cisco_xr",
    "junos": "juniper_junos", "eos": "arista_eos",
    "srlinux": "nokia_srl", "sr-linux": "nokia_srl", "nokia-srlinux": "nokia_srl",
    "sros": "nokia_sros", "vyos": "vyos", "routeros": "mikrotik_routeros",
    "sonic": "dell_sonic", "exos": "extreme_exos", "vrp": "huawei_vrp",
    "edgeos": "ubiquiti_edge", "frr": "frr", "linux": "linux",
}


def _normalise_platform(raw: str | None) -> str | None:
    if not raw:
        return None
    key = str(raw).strip().lower().replace("_", "-")
    return PLATFORM_HINTS.get(key) or PLATFORM_HINTS.get(key.replace("-", "")) or str(raw)


def _credential_ref(record: dict, site: str | None, platform: str | None) -> str:
    """Derive a credential reference — never a credential.

    Prefers an explicit custom field, then site, then platform, then "default".
    That ordering is what makes per-device, per-site and per-platform credentials
    work from a source of truth (FR-020) without any secret leaving Vault or .env.
    """
    cf = record.get("custom_fields") or {}
    for key in ("credential_ref", "netclaw_credential_ref", "credentials"):
        if cf.get(key):
            return str(cf[key])
    return site or platform or "default"


def _from_netbox() -> list[Device]:
    url = os.environ.get("NETBOX_URL")
    token = os.environ.get("NETBOX_TOKEN")
    if not (url and token):
        raise InventoryError("NetBox not configured (NETBOX_URL / NETBOX_TOKEN)")

    import httpx
    from routing import owner_of

    endpoint = url.rstrip("/") + "/api/dcim/devices/"
    try:
        r = httpx.get(endpoint, timeout=25,
                      headers={"Authorization": f"Token {token}",
                               "Accept": "application/json"},
                      params={"limit": 500, "status": "active"})
        r.raise_for_status()
        rows = r.json().get("results", [])
    except Exception as exc:  # noqa: BLE001
        raise InventoryError(f"NetBox query failed: {type(exc).__name__}: {str(exc)[:160]}") from exc

    devices: list[Device] = []
    for row in rows:
        name = row.get("name")
        ip = (row.get("primary_ip") or {}).get("address") or ""
        hostname = ip.split("/")[0] if ip else None
        if not (name and hostname):
            continue  # no address means nothing to connect to
        platform = _normalise_platform((row.get("platform") or {}).get("slug"))
        site = (row.get("site") or {}).get("slug")
        role = (row.get("role") or row.get("device_role") or {}).get("slug")
        groups = [g for g in (site, role) if g]
        devices.append(Device(
            name=name, hostname=hostname, platform=platform,
            credential_ref=_credential_ref(row, site, platform),
            groups=groups, source=Source.LIVE_SOT, owning_server=owner_of(platform),
        ))
    return devices


def _from_nautobot() -> list[Device]:
    url = os.environ.get("NAUTOBOT_URL")
    token = os.environ.get("NAUTOBOT_TOKEN")
    if not (url and token):
        raise InventoryError("Nautobot not configured (NAUTOBOT_URL / NAUTOBOT_TOKEN)")

    import httpx
    from routing import owner_of

    endpoint = url.rstrip("/") + "/api/dcim/devices/"
    try:
        r = httpx.get(endpoint, timeout=25,
                      headers={"Authorization": f"Token {token}",
                               "Accept": "application/json"},
                      params={"limit": 500})
        r.raise_for_status()
        rows = r.json().get("results", [])
    except Exception as exc:  # noqa: BLE001
        raise InventoryError(f"Nautobot query failed: {type(exc).__name__}: {str(exc)[:160]}") from exc

    devices: list[Device] = []
    for row in rows:
        name = row.get("name")
        ip = (row.get("primary_ip4") or row.get("primary_ip") or {}).get("address") or ""
        hostname = ip.split("/")[0] if ip else None
        if not (name and hostname):
            continue
        platform = _normalise_platform((row.get("platform") or {}).get("slug"))
        site = ((row.get("location") or row.get("site") or {}) or {}).get("slug")
        role = (row.get("role") or row.get("device_role") or {}).get("slug")
        groups = [g for g in (site, role) if g]
        devices.append(Device(
            name=name, hostname=hostname, platform=platform,
            credential_ref=_credential_ref(row, site, platform),
            groups=groups, source=Source.LIVE_SOT, owning_server=owner_of(platform),
        ))
    return devices


def load() -> list[Device]:
    """Load from whichever source of truth is configured.

    Tries NetBox then Nautobot. Raises with every attempt's reason when none
    yields devices, so `auto` can fall through to a file tier with an explanation
    rather than presenting an empty fleet as fact.
    """
    reasons: list[str] = []
    for loader, label in ((_from_netbox, "netbox"), (_from_nautobot, "nautobot")):
        try:
            devices = loader()
        except InventoryError as exc:
            reasons.append(f"{label}: {exc}")
            continue
        if devices:
            return devices
        reasons.append(f"{label}: reachable but returned no usable devices "
                       f"(devices need a name and a primary IP)")
    raise InventoryError("no live source of truth available — " + "; ".join(reasons))
