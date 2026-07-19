#!/usr/bin/env python3
"""Generate testbed/testbed.yaml from Nautobot device inventory.

Nautobot is the source of truth. This script queries the Nautobot API for
all active devices with a primary IP and a platform, then generates a pyATS
testbed YAML. Run on-demand or via cron to keep the testbed in sync.

Requires: NAUTOBOT_URL, NAUTOBOT_TOKEN in the environment (or .env).

Platform mapping (Nautobot platform.slug → pyATS os):
  cisco_ios     → ios
  cisco_xe      → iosxe
  cisco_nxos    → nxos
  cisco_asa     → asa
  linux         → linux
  junos         → junos
  pfsense_plus  → linux   (pyATS treats pfSense as linux SSH)
"""

import json
import os
import sys
import urllib.request
import ssl
import yaml
from pathlib import Path

# Platform slug → pyATS os mapping
PLATFORM_MAP = {
    "cisco_ios": "ios",
    "cisco_xe": "iosxe",
    "cisco_nxos": "nxos",
    "cisco_asa": "asa",
    "junos": "junos",
    "linux": "linux",
    "pfsense_plus": "linux",
    "proxmox_ve": "linux",
}

# Device types to SKIP (not SSH-manageable network devices)
SKIP_PLATFORMS = {"none", None}
SKIP_ROLES = set()  # Add role slugs to exclude (e.g. "access-point")

NETCLAW_DIR = os.environ.get("NETCLAW_DIR", str(Path(__file__).resolve().parent.parent))
TESTBED_PATH = os.path.join(NETCLAW_DIR, "testbed", "testbed.yaml")


def load_env():
    """Load .env if vars aren't already set."""
    env_file = os.path.join(NETCLAW_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    val = val.strip().strip('"').strip("'")
                    os.environ.setdefault(key.strip(), val)


def fetch_devices():
    """Query Nautobot for all active devices with primary IPs."""
    url = os.environ["NAUTOBOT_URL"].rstrip("/")
    token = os.environ["NAUTOBOT_TOKEN"]
    verify = os.environ.get("NAUTOBOT_VERIFY_SSL", "true").lower() != "false"

    api_url = f"{url}/api/dcim/devices/?limit=100&depth=1&status=Active&format=json"

    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(api_url, headers={
        "Authorization": f"Token {token}",
        "Accept": "application/json",
    })

    with urllib.request.urlopen(req, context=ctx) as resp:
        data = json.loads(resp.read())

    return data.get("results", [])


def build_testbed(devices):
    """Build pyATS testbed dict from Nautobot device list."""
    testbed = {
        "testbed": {
            "name": "NetClaw-Nautobot-SoT",
            "credentials": {
                "default": {
                    "username": "%ENV{NETCLAW_USERNAME}",
                    "password": "%ENV{NETCLAW_PASSWORD}",
                },
                "enable": {
                    "password": "%ENV{NETCLAW_ENABLE_PASSWORD}",
                },
            },
        },
        "devices": {},
    }

    for dev in devices:
        name = dev.get("name")
        if not name:
            continue

        # Get platform
        platform = dev.get("platform")
        if not platform:
            continue
        plat_slug = platform.get("network_driver", "") or platform.get("napalm_driver", "") or platform.get("display", "").lower().replace(" ", "_")

        # Map to pyATS os
        pyats_os = PLATFORM_MAP.get(plat_slug)
        if not pyats_os:
            # Try display name fallback
            plat_display = platform.get("display", "").lower().replace(" ", "_")
            pyats_os = PLATFORM_MAP.get(plat_display)
            if not pyats_os:
                print(f"  SKIP {name}: unmapped platform '{plat_slug}' / '{plat_display}'")
                continue

        # Get primary IP (strip /prefix)
        ip4 = dev.get("primary_ip4")
        if not ip4:
            continue
        ip_addr = ip4.get("address", "").split("/")[0]
        if not ip_addr:
            continue

        # Determine device type
        dev_type_obj = dev.get("device_type", {})
        role_obj = dev.get("role", {})
        role_display = role_obj.get("display", "").lower() if role_obj else ""

        if "switch" in role_display:
            dev_type = "switch"
        elif "router" in role_display:
            dev_type = "router"
        elif "firewall" in role_display:
            dev_type = "firewall"
        else:
            dev_type = "host"

        # Build device entry
        testbed["devices"][name] = {
            "alias": name,
            "type": dev_type,
            "os": pyats_os,
            "connections": {
                "defaults": {"class": "unicon.Unicon"},
                "ssh": {
                    "protocol": "ssh",
                    "ip": ip_addr,
                    "port": 22,
                },
            },
        }

    return testbed


def main():
    load_env()

    if "NAUTOBOT_URL" not in os.environ or "NAUTOBOT_TOKEN" not in os.environ:
        print("ERROR: NAUTOBOT_URL and NAUTOBOT_TOKEN must be set")
        sys.exit(1)

    print(f"Fetching devices from {os.environ['NAUTOBOT_URL']}...")
    devices = fetch_devices()
    print(f"  Found {len(devices)} active devices")

    testbed = build_testbed(devices)
    dev_count = len(testbed["devices"])
    print(f"  Generated testbed with {dev_count} pyATS-compatible devices")

    # Write testbed
    os.makedirs(os.path.dirname(TESTBED_PATH), exist_ok=True)
    with open(TESTBED_PATH, "w") as f:
        f.write("# Auto-generated from Nautobot — do not hand-edit.\n")
        f.write(f"# Source: {os.environ['NAUTOBOT_URL']}\n")
        f.write(f"# Generated by: scripts/generate-testbed-from-nautobot.py\n\n")
        yaml.dump(testbed, f, default_flow_style=False, sort_keys=False)

    print(f"  Written to: {TESTBED_PATH}")
    print()
    for name, entry in testbed["devices"].items():
        print(f"  {name:30s} os={entry['os']:8s} ip={entry['connections']['ssh']['ip']}")


if __name__ == "__main__":
    main()
