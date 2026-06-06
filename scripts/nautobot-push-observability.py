#!/usr/bin/env python3
"""Push observability + IP SLA to lab devices via Nautobot SoT.

Primary deploy path: Golden Config intended → Ansible build/deploy (full config).
Remediation config plans are NOT used (they bundle unrelated compliance drift).
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys

sys.path.insert(0, "/home/ubuntu/netclaw/mcp-servers/nautobot-golden-config-mcp")

from job_runner import (  # noqa: E402
    JOB_BACKUP,
    JOB_COMPLIANCE,
    JOB_INTENDED,
    run_job_and_wait,
)
from nautobot_client import NautobotClient, NautobotError  # noqa: E402

os.environ.setdefault("NAUTOBOT_URL", "http://localhost:8080")
os.environ.setdefault("NAUTOBOT_TOKEN", "0123456789abcdef0123456789abcdef01234567")
os.environ.setdefault("NAUTOBOT_VERIFY_SSL", "false")
os.environ.setdefault("NAUTOBOT_TIMEOUT", "120")
os.environ.setdefault("GOLDEN_CONFIG_JOB_TIMEOUT", "600")

CONTEXT_NAME = "Observability"
IOS_DEVICES = [
    "P1", "P2", "P3", "P4", "PE1", "PE2", "PE3", "CE1", "CE2", "RR1",
]
ANSIBLE_DIR = os.path.expanduser("~/Nautobot-Workshop/ansible-lab")
DATASOURCE_REPO = os.path.expanduser(
    "~/github-projects/Nautobot-Workshop-Datasource"
)


def _default_observability() -> dict:
    return {
        "mgmt_vrf": "clab-mgmt",
        "snmp": {"community": "public", "access": "ro"},
        "syslog": {
            "host": "192.168.220.200",
            "port": 1514,
            "transport": "udp",
            "trap_level": "informational",
        },
        "bmp": {
            "enabled": True,
            "host": "192.168.220.205",
            "port": 5000,
            "server_id": 1,
            "description": "netclaw-gobmp",
            "initial_refresh_delay": 30,
            "initial_delay": 5,
            "failure_retry_delay": 5,
            "flapping_delay": 30,
        },
        "gnmi": {"enabled": True, "transport": "default", "port": 6030},
    }


async def patch_observability_context(client: NautobotClient) -> None:
    """Sync observability intent: syslog VRF, BMP, gNMI (spec 031 Phase 6)."""
    resp = await client.rest_get("extras/config-contexts", {"name": CONTEXT_NAME})
    results = resp.get("results", [])
    if not results:
        raise RuntimeError(f"Config context '{CONTEXT_NAME}' not found in Nautobot")
    ctx = results[0]
    data = ctx.get("data") or {}
    want = _default_observability()
    obs = data.setdefault("observability", {})
    changed = False
    for key, val in want.items():
        if obs.get(key) != val:
            obs[key] = val
            changed = True
    if changed:
        await client.rest_patch(
            f"extras/config-contexts/{ctx['id']}/",
            {"data": data},
        )
        print("Patched Observability context (mgmt_vrf, bmp, gnmi)")
    else:
        print("Observability context already up to date")


async def resolve_device_ids(client: NautobotClient, names: list[str]) -> list[str]:
    ids = []
    for name in names:
        data = await client.graphql(f'{{ devices(name: "{name}") {{ id }} }}')
        devices_list = data.get("devices", [])
        if not devices_list:
            raise NautobotError(f"Device '{name}' not found")
        ids.append(devices_list[0]["id"])
    return ids


async def regenerate_intended(client: NautobotClient, devices: list[str]) -> None:
    ids = await resolve_device_ids(client, devices)
    data = {"device": ids}
    print(f"\n=== Generate Intended ({len(ids)} devices) ===")
    r = await run_job_and_wait(client, JOB_INTENDED, data, timeout=600)
    print(json.dumps(r, indent=2)[:500])
    print("\n=== Backup ===")
    r = await run_job_and_wait(client, JOB_BACKUP, data, timeout=600)
    print(json.dumps(r, indent=2)[:300])
    print("\n=== Compliance ===")
    r = await run_job_and_wait(client, JOB_COMPLIANCE, data, timeout=600)
    print(json.dumps(r, indent=2)[:300])


def ensure_clab_network() -> None:
    script = """
NAUTOBOT_CONTAINER=$(docker ps --format '{{.Names}}' | grep nautobot-1 | head -1)
CELERY_CONTAINER=$(docker ps --format '{{.Names}}' | grep celery_worker | head -1)
for c in "$NAUTOBOT_CONTAINER" "$CELERY_CONTAINER"; do
  [ -n "$c" ] && docker network connect clab-mgmt "$c" 2>/dev/null || true
done
"""
    subprocess.run(["bash", "-c", script], check=False)


def ansible_deploy() -> int:
    """Build + deploy configs via Ansible (loads device data from Nautobot API)."""
    if not os.path.isdir(ANSIBLE_DIR):
        print(f"ERROR: {ANSIBLE_DIR} not found")
        return 1
    env = os.environ.copy()
    env.setdefault("NAUTOBOT_URL", "http://localhost:8080")
    env.setdefault(
        "NAUTOBOT_TOKEN",
        "0123456789abcdef0123456789abcdef01234567",
    )
    venv_python = os.path.join(ANSIBLE_DIR, ".venv/bin/ansible-playbook")
    if not os.path.isfile(venv_python):
        print("Creating ansible venv...")
        subprocess.run(
            ["python3", "-m", "venv", ".venv"],
            cwd=ANSIBLE_DIR,
            check=True,
        )
        subprocess.run(
            [os.path.join(ANSIBLE_DIR, ".venv/bin/pip"), "install", "-q", "-r", "pip-requirements.txt"],
            cwd=ANSIBLE_DIR,
            check=True,
        )
    for tag in ("build", "deploy"):
        print(f"\n=== Ansible --tags {tag} ===")
        rc = subprocess.run(
            [venv_python, "pb.build-lab.yml", "--tags", tag],
            cwd=ANSIBLE_DIR,
            env=env,
        ).returncode
        if rc != 0:
            print(f"Ansible {tag} exited {rc} (Arista deploy failures are a known lab issue)")
            if tag == "build":
                return rc
    return 0


async def verify_intended(client: NautobotClient) -> None:
    checks = {
        "PE1": {
            "snmp": "snmp-server community public RO",
            "logging_vrf_clab_mgmt": "logging host 192.168.220.200 vrf clab-mgmt",
            "ip_sla": "ip sla 10",
            "no_bmp": "bmp server",
        },
        "RR1": {
            "bmp_server": "bmp server 1",
            "bmp_host": "192.168.220.205",
            "bmp_activate": "bmp-activate server 1",
            "logging_global": "logging host 192.168.220.200 transport udp port 1514",
        },
        "West-Spine01": {
            "gnmi": "management api gnmi",
            "gnmi_grpc": "transport grpc default",
        },
    }
    for device, patterns in checks.items():
        resp = await client.rest_get(
            "plugins/golden-config/golden-config", {"device": device}
        )
        ic = (resp.get("results") or [{}])[0].get("intended_config") or ""
        result = {}
        for name, needle in patterns.items():
            if name == "no_bmp":
                result[name] = needle not in ic
            else:
                result[name] = needle in ic
        print(f"\n{device} intended checks:", result)


async def main() -> int:
    client = NautobotClient()
    ensure_clab_network()
    await patch_observability_context(client)
    await regenerate_intended(client, IOS_DEVICES)
    eos = [
        "West-Spine01", "West-Spine02", "West-Leaf01", "West-Leaf02",
        "East-Spine01", "East-Spine02", "East-Leaf01", "East-Leaf02",
    ]
    await regenerate_intended(client, eos)
    await verify_intended(client)
    rc = ansible_deploy()
    print(
        "\nVerify metrics: curl -s "
        "'http://192.168.220.201:8428/api/v1/query?query=interface_status'"
    )
    if os.path.isdir(DATASOURCE_REPO):
        print(
            f"\nDatasource fix (mgmt_vrf) at {DATASOURCE_REPO}/config_contexts/observability.yml"
            " — push to GitHub then SYNC_DATASOURCE=1 to sync into Nautobot."
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))