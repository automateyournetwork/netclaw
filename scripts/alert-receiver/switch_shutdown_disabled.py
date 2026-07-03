#!/usr/bin/env python3
"""Shutdown a set of interfaces on a switch to match Nautobot intent.

baseline -> apply 'shutdown' -> verify -> save. Reversible via 'no shutdown'.
Reads creds from ~/.openclaw/.env, uses the Nautobot-generated testbed.

Usage:
  switch_shutdown_disabled.py HomeSwitch01 Gi1/0/4 Gi1/0/8 ...
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
ifaces = sys.argv[2:]
if not ifaces:
    print("no interfaces given"); sys.exit(1)

tb = load(os.environ["PYATS_TESTBED_PATH"])
dev = tb.devices[device_name]
dev.connect(log_stdout=False, learn_hostname=True, init_exec_commands=[], init_config_commands=[])

try:
    # 1. Baseline — current admin state of each interface
    print("=== BASELINE (show interfaces status) ===")
    pre = dev.parse("show interfaces status").get("interfaces", {})

    def full(short):
        return short.replace("Gi", "GigabitEthernet")

    for s in ifaces:
        f = full(s)
        st = pre.get(f, {}).get("status", "?")
        print(f"  {f}: {st}")

    # 2. Apply shutdown
    cfg = []
    for s in ifaces:
        cfg += [f"interface {full(s)}", "shutdown"]
    print("\n=== APPLYING shutdown to %d interfaces ===" % len(ifaces))
    dev.configure(cfg)

    # 3. Verify — should now read 'disabled'
    print("\n=== VERIFY (show interfaces status) ===")
    post = dev.parse("show interfaces status").get("interfaces", {})
    ok = 0
    for s in ifaces:
        f = full(s)
        st = post.get(f, {}).get("status", "?")
        marker = "OK" if st == "disabled" else "CHECK"
        if st == "disabled":
            ok += 1
        print(f"  {f}: {st}  [{marker}]")
    print(f"\n{ok}/{len(ifaces)} interfaces now administratively disabled")

    # 4. Save
    print("\n=== SAVING (write memory) ===")
    print(dev.execute("write memory"))
finally:
    dev.disconnect()
