#!/usr/bin/env python3
"""Compare live switch interface admin-state vs Nautobot 'enabled', device = truth.

Reports mismatches. With --apply, PATCHes Nautobot 'enabled' to match the device.
Read creds from ~/.openclaw/.env and netclaw/.env; uses the Nautobot testbed.

Device admin-state: 'show interfaces status' status == 'disabled' -> admin down
(enabled False); anything else (connected/notconnect/err-disabled) -> enabled True.

Usage:
  reconcile_admin_state.py HomeSwitch01 HomeSwitch02          # report only
  reconcile_admin_state.py --apply HomeSwitch01 HomeSwitch02  # sync Nautobot
"""
import json
import os
import ssl
import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO = Path("/home/ubuntu/netclaw")


def load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


load_env(REPO / ".env")
load_env(Path.home() / ".openclaw/.env")
os.environ.setdefault("PYATS_TESTBED_PATH", str(REPO / "testbed/testbed.yaml"))

NB = (os.environ.get("NAUTOBOT_URL") or "https://nautobot.internal.byrnbaker.me").rstrip("/")
TOK = os.environ.get("NAUTOBOT_TOKEN", "")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

APPLY = "--apply" in sys.argv
devices = [a for a in sys.argv[1:] if not a.startswith("--")]


def nb_api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        NB + path, data=data, method=method,
        headers={"Authorization": "Token " + TOK,
                 "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as r:
        return json.load(r)


def nb_interfaces(device):
    out, url = {}, f"/api/dcim/interfaces/?device={device}&limit=200"
    while url:
        d = nb_api("GET", url)
        for i in d.get("results", []):
            out[i["name"]] = {"id": i["id"], "enabled": i["enabled"]}
        nxt = d.get("next")
        url = nxt.replace(NB, "") if nxt else None
    return out


from genie.testbed import load  # noqa: E402

tb = load(os.environ["PYATS_TESTBED_PATH"])

total_mismatch = 0
for dname in devices:
    dev = tb.devices[dname]
    dev.connect(log_stdout=False, learn_hostname=True,
                init_exec_commands=[], init_config_commands=[])
    try:
        rows = dev.parse("show interfaces status").get("interfaces", {})
    finally:
        dev.disconnect()

    dev_enabled = {name: (d.get("status") != "disabled") for name, d in rows.items()}
    nb = nb_interfaces(dname)

    print(f"\n===== {dname} — mismatches (device -> nautobot) =====")
    mism = []
    for name, dev_en in dev_enabled.items():
        if name not in nb:
            continue  # interface not modeled in Nautobot; skip
        if nb[name]["enabled"] != dev_en:
            mism.append((name, nb[name]["enabled"], dev_en, nb[name]["id"]))

    if not mism:
        print("  (in sync)")
    for name, nb_en, dev_en, iid in sorted(mism):
        print(f"  {name:24} nautobot.enabled={nb_en!s:5} -> device={dev_en!s:5}")
        if APPLY:
            nb_api("PATCH", f"/api/dcim/interfaces/{iid}/", {"enabled": dev_en})
    total_mismatch += len(mism)
    print(f"  {len(mism)} mismatch(es){' — APPLIED' if (APPLY and mism) else ''}")

print(f"\nTOTAL: {total_mismatch} mismatch(es){' applied' if APPLY else ' (report only)'}")
