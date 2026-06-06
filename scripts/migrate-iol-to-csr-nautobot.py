#!/usr/bin/env python3
"""Migrate Nautobot workshop IOS routers from IOL to CSR1000v interface naming."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

NAUTOBOT_URL = os.environ.get("NAUTOBOT_URL", "http://127.0.0.1:8080")
NAUTOBOT_TOKEN = os.environ.get(
    "NAUTOBOT_TOKEN", "0123456789abcdef0123456789abcdef01234567"
)

IOS_DEVICES = [
    "P1", "P2", "P3", "P4", "PE1", "PE2", "PE3", "CE1", "CE2", "RR1",
]

INTERFACE_MAP = {
    "Ethernet0/0": "GigabitEthernet1",
    "Ethernet0/1": "GigabitEthernet2",
    "Ethernet0/2": "GigabitEthernet3",
    "Ethernet0/3": "GigabitEthernet4",
    "Ethernet1/0": "GigabitEthernet5",
}


def api(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{NAUTOBOT_URL}{path}"
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Token {NAUTOBOT_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"{method} {path} -> {exc.code}: {detail}") from exc


def get_first(path: str, **params) -> dict | None:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    result = api("GET", f"{path}?{query}" if query else path)
    items = result.get("results", [])
    return items[0] if items else None


def ensure_device_type(model: str, manufacturer_id: str) -> str:
    existing = get_first("/api/dcim/device-types/", model=model)
    if existing:
        return existing["id"]
    created = api(
        "POST",
        "/api/dcim/device-types/",
        {
            "manufacturer": manufacturer_id,
            "model": model,
            "slug": model,
            "u_height": 1,
        },
    )
    print(f"Created device type {model}: {created['id']}")
    return created["id"]


def ensure_software_version(version: str, platform_id: str) -> str:
    existing = get_first("/api/dcim/software-versions/", version=version)
    if existing:
        return existing["id"]
    created = api(
        "POST",
        "/api/dcim/software-versions/",
        {
            "version": version,
            "platform": platform_id,
            "status": get_first("/api/extras/statuses/", name="Active")["id"],
        },
    )
    print(f"Created software version {version}: {created['id']}")
    return created["id"]


def migrate_device(device_name: str, device_type_id: str, software_version_id: str) -> None:
    device = get_first("/api/dcim/devices/", name=device_name)
    if not device:
        raise RuntimeError(f"Device {device_name} not found")

    interfaces = api(
        "GET",
        f"/api/dcim/interfaces/?device_id={device['id']}&limit=100",
    )["results"]

    renamed = 0
    for intf in interfaces:
        old_name = intf["name"]
        if old_name not in INTERFACE_MAP:
            continue
        new_name = INTERFACE_MAP[old_name]
        patch = {"name": new_name}
        if new_name == "GigabitEthernet1":
            patch["mgmt_only"] = True
        api("PATCH", f"/api/dcim/interfaces/{intf['id']}/", patch)
        print(f"  {device_name}: {old_name} -> {new_name}")
        renamed += 1

    api(
        "PATCH",
        f"/api/dcim/devices/{device['id']}/",
        {
            "device_type": device_type_id,
            "software_version": software_version_id,
        },
    )
    print(f"Updated {device_name}: device_type=csr1000v software_version=17.03.08a ({renamed} interfaces renamed)")


def main() -> int:
    cisco = get_first("/api/dcim/manufacturers/", name="Cisco")
    ios = get_first("/api/dcim/platforms/", name="IOS")
    if not cisco or not ios:
        print("Cisco manufacturer or IOS platform missing", file=sys.stderr)
        return 1

    csr_type_id = ensure_device_type("csr1000v", cisco["id"])
    sw_id = ensure_software_version("17.03.08a", ios["id"])

    print("Migrating IOS lab routers...")
    for name in IOS_DEVICES:
        migrate_device(name, csr_type_id, sw_id)

    device = get_first("/api/dcim/devices/", name="P1")
    ifaces = api("GET", f"/api/dcim/interfaces/?device_id={device['id']}&limit=50")["results"]
    print("\nP1 verification:")
    for intf in sorted(ifaces, key=lambda x: x["name"]):
        print(f"  {intf['name']} mgmt={intf.get('mgmt_only')}")

    dev = api("GET", f"/api/dcim/devices/{device['id']}/?depth=1")
    print(
        f"  device_type={dev['device_type']['model']} "
        f"software={dev['software_version']['version']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())