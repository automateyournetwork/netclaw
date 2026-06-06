#!/usr/bin/env python3
"""Push SNMP/syslog (and IP SLA on PE/CE) from Nautobot-Workshop-Datasource contexts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

os.environ.setdefault("PYATS_TESTBED_PATH", "/home/ubuntu/netclaw/testbed/testbed.yaml")

# Reuse pyATS MCP connection + configure helpers
sys.path.insert(0, "/home/ubuntu/netclaw/mcp-servers/pyATS_MCP")
from pyats_mcp_server import _execute_config  # noqa: E402

DATASOURCE = Path("/home/ubuntu/github-projects/Nautobot-Workshop-Datasource/config_contexts")

OBS_LINES = [
    "snmp-server community public RO",
    "logging on",
    "logging host 192.168.220.200 vrf clab-mgmt transport udp port 1514",
    "logging trap informational",
]

IP_SLA_DEVICES = {"PE1", "PE2", "PE3", "CE1", "CE2"}

ARISTA_OBS = [
    "snmp-server community public ro",
    "logging host 192.168.220.200 1514 protocol udp",
    "logging trap informational",
]


def load_ip_sla(device: str) -> list[str]:
    ctx_file = DATASOURCE / "devices" / f"{device}.yml"
    if not ctx_file.exists():
        return []
    data = yaml.safe_load(ctx_file.read_text()) or {}
    sla = data.get("ip_sla")
    if not sla:
        return []
    lines: list[str] = []
    for probe in sla.get("probes", []):
        pid = probe["id"]
        lines.append(f"ip sla {pid}")
        if probe["type"] == "jitter":
            lines.append(
                f" udp-jitter {probe['destination']} {probe['port']} "
                f"num-packets {probe.get('num_packets', 100)}"
            )
            lines.append(f" frequency {probe.get('frequency', 60)}")
            lines.append(f" threshold {probe.get('threshold', 3000)}")
            lines.append(f" owner netclaw-jitter-{pid}")
        elif probe["type"] == "icmp-echo":
            lines.append(f" icmp-echo {probe['destination']}")
            lines.append(f" frequency {probe.get('frequency', 60)}")
            lines.append(f" threshold {probe.get('threshold', 5000)}")
            lines.append(f" owner netclaw-icmp-echo-{pid}")
        lines.append(f"ip sla schedule {pid} life forever start-time now")
    if sla.get("responder"):
        lines.append("ip sla responder")
    return lines


def main() -> int:
    ios = ["P1", "P2", "P3", "P4", "PE1", "PE2", "PE3", "CE1", "CE2", "RR1"]
    arista = [
        "West-Spine01", "West-Spine02", "West-Leaf01", "West-Leaf02",
        "East-Spine01", "East-Spine02", "East-Leaf01", "East-Leaf02",
    ]

    ok = fail = 0
    for name in ios:
        cmds = list(OBS_LINES)
        if name in IP_SLA_DEVICES:
            cmds.extend(load_ip_sla(name))
        result = _execute_config(name, cmds)
        print(f"{name}: {result.get('status')} — {result.get('error') or result.get('message', '')}")
        ok += result.get("status") == "success"
        fail += result.get("status") != "success"

    for name in arista:
        result = _execute_config(name, ARISTA_OBS)
        print(f"{name}: {result.get('status')} — {result.get('error') or result.get('message', '')}")
        ok += result.get("status") == "success"
        fail += result.get("status") != "success"

    print(f"Done: {ok} ok, {fail} failed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())