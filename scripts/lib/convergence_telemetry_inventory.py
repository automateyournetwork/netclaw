#!/usr/bin/env python3
"""Convergence telemetry inventory helpers (Phase 10 PR2).

Shared by setup wizard and smoke: list devices from Nautobot/NetBox,
normalize targets, merge into convergence.yaml.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError as e:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from e

VALID_TEMPLATES = ("cisco", "pfsense", "generic")
VALID_ROLES = ("switch", "firewall", "other")

# Roles that are good SNMP candidates by default (exclude pure wireless APs)
DEFAULT_INCLUDE_ROLE_SUBSTR = (
    "switch",
    "router",
    "firewall",
    "core",
    "access",
    "dist",
    "spine",
    "leaf",
    "edge",
    "gateway",
    "pfsense",
)
DEFAULT_EXCLUDE_ROLE_SUBSTR = (
    "wireless",
    "wifi",
    "access-point",
    "access_point",
    "ap-",
    "wlc",
    "phone",
    "camera",
    "pdu",
    "ups",
    # compute / hypervisor / cluster nodes — not campus SNMP targets
    "server",
    "k3s",
    "worker",
    "hypervisor",
    "proxmox",
    "pve",
    "vmhost",
    "compute",
    "baremetal",
    "bmc",
)

PLATFORM_TO_VENDOR = {
    "cisco_ios": "cisco",
    "cisco_iosxe": "cisco",
    "cisco_xe": "cisco",
    "cisco_nxos": "nxos",
    "cisco_iosxr": "cisco",
    "ios": "cisco",
    "iosxe": "cisco",
    "nxos": "nxos",
    "arista_eos": "arista",
    "eos": "arista",
    "juniper_junos": "juniper",
    "junos": "juniper",
    "cumulus": "cumulus",
    "sonic": "sonic",
    "pfsense": "pfsense",
    "opnsense": "pfsense",
}


def load_dotenv_files(paths: list[Path]) -> None:
    """Minimal .env loader (KEY=VAL); does not override existing env."""
    for path in paths:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = val


def normalize_template(vendor: str | None, template: str | None) -> str:
    t = (template or vendor or "generic").strip().lower()
    if t in ("ios", "ios-xe", "iosxe", "catalyst", "nxos", "cisco_ios", "cisco_xe", "cisco_iosxe"):
        return "cisco"
    if t in ("pf", "pfsense-fw", "firewall-pfsense", "opnsense"):
        return "pfsense" if "opnsense" not in t else "generic"
    if t not in VALID_TEMPLATES:
        return "generic"
    return t


def normalize_target(raw: dict) -> dict | None:
    ip = (raw.get("ip") or raw.get("address") or "").strip()
    if not ip:
        return None
    # strip CIDR if present
    ip = ip.split("/")[0].strip()
    name = (raw.get("name") or ip).strip()
    role = (raw.get("role") or "switch").strip().lower()
    if role not in VALID_ROLES:
        if "firewall" in role or "pfsense" in role:
            role = "firewall"
        elif "switch" in role or "router" in role or "core" in role:
            role = "switch"
        else:
            role = "other" if role not in VALID_ROLES else role
            if role not in VALID_ROLES:
                role = "switch"
    vendor = (raw.get("vendor") or "").strip().lower() or None
    template = normalize_template(vendor, raw.get("template"))
    if not vendor:
        vendor = template
    return {
        "name": name,
        "ip": ip,
        "role": role,
        "vendor": vendor,
        "template": template,
    }


def sort_targets(targets: list[dict]) -> list[dict]:
    return sorted(targets, key=lambda t: (t["name"].lower(), t["ip"]))


def _strip_ip(primary: Any) -> str:
    if not primary:
        return ""
    if isinstance(primary, dict):
        addr = primary.get("address") or primary.get("host") or ""
        return str(addr).split("/")[0].strip()
    return str(primary).split("/")[0].strip()


def _role_fields(device: dict) -> tuple[str, str]:
    role = device.get("role") or device.get("device_role") or {}
    if isinstance(role, dict):
        return (
            (role.get("name") or "").lower(),
            (role.get("slug") or "").lower(),
        )
    return str(role).lower(), ""


def _platform_slug(device: dict) -> str:
    platform = device.get("platform") or {}
    if isinstance(platform, dict):
        return (
            platform.get("network_driver")
            or platform.get("slug")
            or platform.get("name")
            or ""
        ).lower()
    return str(platform).lower()


def infer_vendor_template(device: dict) -> tuple[str, str]:
    """Return (vendor, template) from platform/name/role."""
    plat = _platform_slug(device)
    name = (device.get("name") or "").lower()
    role_name, role_slug = _role_fields(device)
    blob = f"{plat} {name} {role_name} {role_slug}"

    if "pfsense" in blob or "opnsense" in blob:
        return "pfsense", "pfsense"
    for key, vendor in PLATFORM_TO_VENDOR.items():
        if key in plat or key in blob:
            tmpl = normalize_template(vendor, vendor)
            return vendor, tmpl
    if "cisco" in blob or "catalyst" in blob or "ios" in blob:
        return "cisco", "cisco"
    return "generic", "generic"


def infer_role(device: dict) -> str:
    role_name, role_slug = _role_fields(device)
    name = (device.get("name") or "").lower()
    blob = f"{role_name} {role_slug} {name}"
    if "firewall" in blob or "pfsense" in blob:
        return "firewall"
    if any(x in blob for x in ("switch", "router", "core", "access", "spine", "leaf")):
        return "switch"
    return "switch"


def is_snmp_candidate(
    device: dict,
    *,
    include_wireless: bool = False,
    include_servers: bool = False,
    role_filter: str | None = None,
) -> bool:
    role_name, role_slug = _role_fields(device)
    name = (device.get("name") or "").lower()
    blob = f"{role_name} {role_slug} {name}"
    if role_filter:
        if role_filter.lower() not in blob:
            return False
    if not include_wireless:
        for ex in (
            "wireless",
            "wifi",
            "access-point",
            "access_point",
            "ap-",
            "wlc",
        ):
            if ex in blob:
                return False
    if not include_servers:
        for ex in DEFAULT_EXCLUDE_ROLE_SUBSTR:
            if ex in (
                "wireless",
                "wifi",
                "access-point",
                "access_point",
                "ap-",
                "wlc",
                "phone",
                "camera",
                "pdu",
                "ups",
            ):
                continue  # handled above / always excluded noise
            if ex in blob:
                return False
        # name-based compute hints
        for ex in ("k3s-", "pve", "proxmox", "-server-", "r640", "esxi"):
            if ex in name:
                return False
    # Prefer known network infrastructure roles
    for inc in DEFAULT_INCLUDE_ROLE_SUBSTR:
        if inc in blob:
            return True
    # Platform-based: cisco / pfsense always candidates
    plat = _platform_slug(device)
    if any(x in plat for x in ("cisco", "ios", "pfsense", "nxos", "eos", "junos")):
        return True
    # Strict default: only include when role/platform looks networked
    return False


def device_to_target(device: dict) -> dict | None:
    name = (device.get("name") or "").strip()
    ip = _strip_ip(device.get("primary_ip4") or device.get("primary_ip") or device.get("primary_ip6"))
    if not name or not ip:
        return None
    vendor, template = infer_vendor_template(device)
    role = infer_role(device)
    return normalize_target(
        {
            "name": name,
            "ip": ip,
            "role": role,
            "vendor": vendor,
            "template": template,
        }
    )


def _http_get_paginated(
    base_url: str,
    endpoint: str,
    *,
    token: str,
    auth_header: str,
    verify: bool,
    params: dict | None = None,
    timeout: float = 30.0,
) -> list[dict]:
    try:
        import httpx  # type: ignore
    except ImportError as e:
        raise RuntimeError("httpx required for SoT mode: pip install httpx") from e

    headers = {
        auth_header: token if auth_header.lower().startswith("author") else token,
        "Accept": "application/json",
    }
    # Nautobot uses Authorization: Token <tok>; NetBox same or Token
    if not auth_header.lower().startswith("authorization"):
        headers = {"Authorization": f"Token {token}", "Accept": "application/json"}
    else:
        headers = {"Authorization": f"Token {token}", "Accept": "application/json"}

    results: list[dict] = []
    url = f"{base_url.rstrip('/')}/api/{endpoint.lstrip('/')}"
    if not url.endswith("/") and "?" not in url:
        url += "/"

    with httpx.Client(verify=verify, timeout=timeout) as client:
        page_params = dict(params or {})
        while url:
            resp = client.get(url, headers=headers, params=page_params or None)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                results.extend(data)
                break
            results.extend(data.get("results") or [])
            url = data.get("next") or ""
            page_params = {}  # next URL already encoded
    return results


def list_nautobot_devices(
    *,
    url: str | None = None,
    token: str | None = None,
    verify: bool | None = None,
    include_wireless: bool = False,
    include_servers: bool = False,
    role_filter: str | None = None,
    status: str = "Active",
) -> list[dict]:
    """Return normalized SNMP targets from Nautobot dcim/devices."""
    base = (url or os.environ.get("NAUTOBOT_URL") or "").rstrip("/")
    tok = token or os.environ.get("NAUTOBOT_TOKEN") or ""
    if verify is None:
        verify = os.environ.get("NAUTOBOT_VERIFY_SSL", "false").lower() in (
            "1",
            "true",
            "yes",
        )
    if not base or not tok:
        raise RuntimeError("NAUTOBOT_URL and NAUTOBOT_TOKEN required")

    raw = _http_get_paginated(
        base,
        "dcim/devices",
        token=tok,
        auth_header="Authorization",
        verify=verify,
        params={"status": status, "depth": "1"},
    )
    out: list[dict] = []
    for d in raw:
        if not is_snmp_candidate(
            d,
            include_wireless=include_wireless,
            include_servers=include_servers,
            role_filter=role_filter,
        ):
            continue
        t = device_to_target(d)
        if t:
            out.append(t)
    return sort_targets(out)


def list_netbox_devices(
    *,
    url: str | None = None,
    token: str | None = None,
    verify: bool | None = None,
    include_wireless: bool = False,
    include_servers: bool = False,
    role_filter: str | None = None,
    status: str = "active",
) -> list[dict]:
    """Return normalized SNMP targets from NetBox dcim/devices (same field shape)."""
    base = (url or os.environ.get("NETBOX_URL") or "").rstrip("/")
    tok = token or os.environ.get("NETBOX_TOKEN") or ""
    if verify is None:
        verify = os.environ.get("NETBOX_VERIFY_SSL", "false").lower() in (
            "1",
            "true",
            "yes",
        )
    if not base or not tok:
        raise RuntimeError("NETBOX_URL and NETBOX_TOKEN required")

    # NetBox uses lowercase status often
    raw = _http_get_paginated(
        base,
        "dcim/devices",
        token=tok,
        auth_header="Authorization",
        verify=verify,
        params={"status": status, "depth": "1"},
    )
    out: list[dict] = []
    for d in raw:
        if not is_snmp_candidate(
            d,
            include_wireless=include_wireless,
            include_servers=include_servers,
            role_filter=role_filter,
        ):
            continue
        t = device_to_target(d)
        if t:
            out.append(t)
    return sort_targets(out)


def parse_csv_targets(csv_text: str) -> list[dict]:
    """Parse name=ip[,name=ip…] or name=ip:vendor into targets."""
    out: list[dict] = []
    for part in re.split(r"[,\n;]+", csv_text or ""):
        part = part.strip()
        if not part:
            continue
        vendor = None
        template = None
        role = "switch"
        # name=ip[:vendor][:role]
        if "=" not in part:
            # bare IP
            out.append(
                normalize_target({"name": part, "ip": part, "role": role})  # type: ignore
            )
            continue
        name, _, rest = part.partition("=")
        bits = rest.split(":")
        ip = bits[0].strip()
        if len(bits) > 1 and bits[1].strip():
            vendor = bits[1].strip().lower()
            template = vendor
        if len(bits) > 2 and bits[2].strip():
            role = bits[2].strip().lower()
        t = normalize_target(
            {"name": name.strip() or ip, "ip": ip, "role": role, "vendor": vendor, "template": template}
        )
        if t:
            out.append(t)
    return sort_targets(out)


def targets_from_yaml_file(path: Path) -> list[dict]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(doc, list):
        raw_list = doc
    else:
        raw_list = doc.get("targets") or []
        # also accept device_telemetry.snmp.targets
        if not raw_list and "device_telemetry" in doc:
            raw_list = (
                (doc.get("device_telemetry") or {}).get("snmp") or {}
            ).get("targets") or []
    out: list[dict] = []
    for t in raw_list:
        n = normalize_target(t if isinstance(t, dict) else {})
        if n:
            out.append(n)
    return sort_targets(out)


def select_by_spec(candidates: list[dict], spec: str) -> list[dict]:
    """Select targets by 'all', comma indices (1-based), or name globs."""
    spec = (spec or "").strip()
    if not spec or spec.lower() in ("all", "*"):
        return list(candidates)
    selected: list[dict] = []
    seen: set[str] = set()
    for token in re.split(r"[,\s]+", spec):
        token = token.strip()
        if not token:
            continue
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(candidates):
                t = candidates[idx]
                key = f"{t['name']}|{t['ip']}"
                if key not in seen:
                    selected.append(t)
                    seen.add(key)
            continue
        # name substring match (case-insensitive)
        needle = token.lower()
        for t in candidates:
            if needle in t["name"].lower() or needle == t["ip"]:
                key = f"{t['name']}|{t['ip']}"
                if key not in seen:
                    selected.append(t)
                    seen.add(key)
    return selected


def load_convergence(path: Path) -> dict:
    if not path.is_file():
        return {
            "site": "home",
            "deploy": "docker",
            "device_telemetry": {"snmp": {"enabled": True, "targets": []}},
        }
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def merge_targets_into_config(
    cfg: dict,
    targets: list[dict],
    *,
    enabled: bool = True,
    replace: bool = True,
) -> dict:
    """Write targets into device_telemetry.snmp; return mutated cfg."""
    dt = cfg.setdefault("device_telemetry", {})
    snmp = dt.setdefault("snmp", {})
    snmp["enabled"] = enabled
    snmp.setdefault("engine", "snmp_exporter")
    snmp.setdefault("version", "v2c")
    snmp.setdefault("poll_interval", "60s")
    if replace:
        snmp["targets"] = list(targets)
    else:
        existing = {
            f"{t.get('name')}|{t.get('ip')}": t for t in (snmp.get("targets") or [])
        }
        for t in targets:
            existing[f"{t['name']}|{t['ip']}"] = t
        snmp["targets"] = sort_targets(
            [normalize_target(x) for x in existing.values() if normalize_target(x)]  # type: ignore
        )
    return cfg


def write_convergence(path: Path, cfg: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Prefer block style for readability
    text = yaml.dump(
        cfg,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )
    path.write_text(text, encoding="utf-8")


def format_targets_table(targets: list[dict]) -> str:
    if not targets:
        return "(no devices)"
    lines = [
        f"{' #':>3}  {'name':<28} {'ip':<16} {'role':<10} {'vendor':<10} template"
    ]
    lines.append("-" * 90)
    for i, t in enumerate(targets, 1):
        lines.append(
            f"{i:3d}  {t['name']:<28} {t['ip']:<16} {t['role']:<10} "
            f"{t['vendor']:<10} {t['template']}"
        )
    return "\n".join(lines)


def write_targets_yaml(path: Path, targets: list[dict], site: str = "home") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"site": site, "targets": targets}
    path.write_text(
        yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
