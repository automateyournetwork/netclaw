#!/usr/bin/env python3
"""READ-ONLY: show live status of specific interfaces on a switch via pyATS.

Reads device creds from ~/.openclaw/.env, loads the Nautobot-generated testbed,
connects to the device, runs 'show interfaces status', and prints the rows for
the interfaces passed on argv. No config changes.

Usage:
  switch_iface_status.py HomeSwitch01 Gi1/0/4 Gi1/0/8 ...
"""
import os
import sys
from pathlib import Path


def load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


load_env(Path.home() / ".openclaw/.env")
os.environ.setdefault("PYATS_TESTBED_PATH", "/home/ubuntu/netclaw/testbed/testbed.yaml")

from genie.testbed import load  # noqa: E402

device_name = sys.argv[1]
want = set(sys.argv[2:])  # short names like Gi1/0/4; we match by suffix

tb = load(os.environ["PYATS_TESTBED_PATH"])
dev = tb.devices[device_name]
dev.connect(log_stdout=False, learn_hostname=True, init_exec_commands=[], init_config_commands=[])
try:
    out = dev.parse("show interfaces status")
finally:
    dev.disconnect()

rows = out.get("interfaces", {})


def norm(n):
    return n.replace("GigabitEthernet", "Gi").replace("TenGigabitEthernet", "Te")


def matches(full):
    s = norm(full)
    return any(s.endswith(norm(w)) or norm(w).endswith(s) or norm(w) == s for w in want) if want else True

print(f"{'interface':22} {'status':14} {'vlan':8} {'name/desc'}")
for full, d in rows.items():
    if not matches(full):
        continue
    print(f"{full:22} {d.get('status',''):14} {str(d.get('vlan','')):8} {d.get('name','')}")
