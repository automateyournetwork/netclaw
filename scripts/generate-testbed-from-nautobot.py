#!/usr/bin/env python3
"""Generate a pyATS testbed.yaml from Nautobot device inventory.

Queries Nautobot for all active devices with primary IPs and generates
a testbed file that pyATS can load. This ensures pyATS always uses
Nautobot as the source of truth for device connectivity.

Usage:
    .venv/bin/python3 scripts/generate-testbed-from-nautobot.py

Environment:
    NAUTOBOT_URL      - Nautobot base URL (e.g., https://192.168.3.253/)
    NAUTOBOT_TOKEN    - API token
    NAUTOBOT_VERIFY_SSL - "true" or "false" (default: false)
    NETCLAW_USERNAME  - Default device SSH username
    NETCLAW_PASSWORD  - Default device SSH password
    PYATS_TESTBED_PATH - Output path (default: testbed/testbed.yaml)
"""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load env from netclaw/.env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

NAUTOBOT_URL = os.getenv("NAUTOBOT_URL", "").rstrip("/")
NAUTOBOT_TOKEN = os.getenv("NAUTOBOT_TOKEN", "")
VERIFY_SSL = os.getenv("NAUTOBOT_VERIFY_SSL", "false").lower() == "true"
USERNAME = os.getenv("NETCLAW_USERNAME", "admin")
PASSWORD = os.getenv("NETCLAW_PASSWORD", "admin")
OUTPUT_PATH = Path(os.getenv("PYATS_TESTBED_PATH", "testbed/testbed.yaml"))

# Legacy SSH key exchange for old Cisco IOS/IOS-XE switches (Catalyst 3850, etc.)
# that modern OpenSSH refuses by default. Appended to the unicon ssh command.
LEGACY_SSH_OPTIONS = (
    "-o KexAlgorithms=+diffie-hellman-group-exchange-sha1,diffie-hellman-group14-sha1"
)

# Map Nautobot platform slugs/network_drivers to pyATS os types
PLATFORM_MAP = {
    "cisco_ios": "ios",
    "cisco_iosxe": "iosxe",
    "cisco_xe": "iosxe",
    "cisco_nxos": "nxos",
    "cisco_iosxr": "iosxr",
    "arista_eos": "eos",
    "juniper_junos": "junos",
    "linux": "linux",
}

# Device roles to exclude from pyATS testbed (managed by other MCP tools)
EXCLUDED_ROLES = {"firewall", "pfsense"}


def query_nautobot(endpoint: str, params: dict = None) -> list:
    """Query Nautobot REST API and return results."""
    headers = {
        "Authorization": f"Token {NAUTOBOT_TOKEN}",
        "Accept": "application/json",
    }
    results = []
    url = f"{NAUTOBOT_URL}/api/{endpoint}/"

    with httpx.Client(verify=VERIFY_SSL, timeout=30) as client:
        while url:
            resp = client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("results", []))
            url = data.get("next")
            params = None  # next URL already has params

    return results


def get_devices() -> list:
    """Get all active devices with primary IPs from Nautobot."""
    devices = query_nautobot("dcim/devices", {"status": "Active", "depth": "1"})
    # Filter to only devices with primary IP
    return [d for d in devices if d.get("primary_ip4") or d.get("primary_ip6")]


def get_platform_slug(device: dict) -> str:
    """Extract platform slug from device data."""
    platform = device.get("platform")
    if platform and isinstance(platform, dict):
        return platform.get("network_driver", "") or platform.get("slug", "")
    return ""


def device_to_testbed_entry(device: dict) -> dict | None:
    """Convert a Nautobot device to a pyATS testbed device entry."""
    name = device.get("name")
    if not name:
        return None

    # Skip devices managed by other MCP tools (e.g., pfSense)
    role = device.get("role", {})
    role_name = role.get("name", "").lower() if isinstance(role, dict) else ""
    role_slug = role.get("slug", "").lower() if isinstance(role, dict) else ""
    if role_name in EXCLUDED_ROLES or role_slug in EXCLUDED_ROLES:
        return None
    if "pfsense" in name.lower() or "firewall" in role_name:
        return None

    # Get primary IP (strip /prefix)
    primary_ip = device.get("primary_ip4") or device.get("primary_ip6")
    if not primary_ip:
        return None

    # Handle both nested object (depth=0) and expanded (depth=1) formats
    if isinstance(primary_ip, dict):
        ip_address = primary_ip.get("address", "").split("/")[0]
        if not ip_address and "host" in primary_ip:
            ip_address = primary_ip["host"]
        # If it's just a reference (no address field), we can't use it
        if not ip_address:
            return None
    else:
        ip_address = str(primary_ip).split("/")[0]

    if not ip_address:
        return None

    # Determine OS type
    platform_slug = get_platform_slug(device)
    os_type = PLATFORM_MAP.get(platform_slug, "")

    if not os_type:
        # Try to infer from device role or name
        role = device.get("role", {})
        role_name = role.get("name", "").lower() if isinstance(role, dict) else ""
        if "spine" in name.lower() or "leaf" in name.lower() or "eos" in platform_slug:
            os_type = "eos"
        elif any(x in role_name for x in ["router", "provider", "reflector", "edge"]):
            os_type = "iosxe"
        else:
            os_type = "iosxe"  # default for unknown

    # Determine device type
    role = device.get("role", {})
    role_name = role.get("name", "").lower() if isinstance(role, dict) else ""
    device_type = "router" if "router" in role_name or "reflector" in role_name else "switch"

    cli = {
        "protocol": "ssh",
        "ip": ip_address,
    }
    # Old Cisco IOS/IOS-XE switches (e.g., Catalyst 3850) only negotiate legacy
    # DH key exchange, which modern OpenSSH rejects. Pass the legacy algorithms so
    # unicon's ssh handshake succeeds. Harmless on newer boxes ('+' only adds algos).
    if os_type in ("iosxe", "ios"):
        cli["ssh_options"] = LEGACY_SSH_OPTIONS

    entry = {
        "os": os_type,
        "type": device_type,
        "connections": {
            "defaults": {"class": "unicon.Unicon"},
            "cli": cli,
        },
    }

    return name, entry


def generate_testbed(devices: list) -> str:
    """Generate testbed YAML content from device list."""
    lines = [
        "# Auto-generated from Nautobot — do not edit manually",
        "# Regenerate: .venv/bin/python3 scripts/generate-testbed-from-nautobot.py",
        f"# Source: {NAUTOBOT_URL}",
        f"# Devices: {len(devices)} active with primary IP",
        "",
        "testbed:",
        "  name: Nautobot-Managed",
        "  credentials:",
        "    default:",
        f"      username: \"%ENV{{NETCLAW_USERNAME}}\"",
        f"      password: \"%ENV{{NETCLAW_PASSWORD}}\"",
        "",
        "devices:",
    ]

    for device in sorted(devices, key=lambda d: d.get("name", "")):
        result = device_to_testbed_entry(device)
        if result is None:
            continue
        name, entry = result

        lines.append(f"  {name}:")
        lines.append(f"    os: {entry['os']}")
        lines.append(f"    type: {entry['type']}")
        lines.append(f"    connections:")
        lines.append(f"      defaults:")
        lines.append(f"        class: unicon.Unicon")
        lines.append(f"      cli:")
        lines.append(f"        protocol: ssh")
        lines.append(f"        ip: {entry['connections']['cli']['ip']}")
        if entry["connections"]["cli"].get("ssh_options"):
            lines.append(f"        ssh_options: {entry['connections']['cli']['ssh_options']}")

    lines.append("")
    return "\n".join(lines)


def main():
    if not NAUTOBOT_URL or not NAUTOBOT_TOKEN:
        print("ERROR: NAUTOBOT_URL and NAUTOBOT_TOKEN must be set in .env", file=sys.stderr)
        sys.exit(1)

    print(f"Querying Nautobot at {NAUTOBOT_URL} for active devices...")
    devices = get_devices()
    print(f"Found {len(devices)} active devices with primary IPs")

    if not devices:
        print("WARNING: No devices found. Check Nautobot connection and device status.", file=sys.stderr)
        sys.exit(1)

    testbed_content = generate_testbed(devices)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(testbed_content)
    print(f"Wrote testbed to {OUTPUT_PATH} ({len(devices)} devices)")

    # Show summary
    from collections import Counter
    os_counts = Counter()
    for d in devices:
        slug = get_platform_slug(d)
        os_counts[PLATFORM_MAP.get(slug, slug or "unknown")] += 1
    for os_type, count in os_counts.most_common():
        print(f"  {os_type}: {count}")


if __name__ == "__main__":
    main()
